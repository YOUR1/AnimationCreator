"""Server-Sent Events (SSE) endpoint for live updates."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, AsyncGenerator

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.middleware import AuthenticatedUser

router = APIRouter(prefix="/api/events", tags=["events"])
settings = get_settings()
logger = logging.getLogger(__name__)

# Redis connection pool (lazily initialized)
_redis_pool: redis.ConnectionPool | None = None


async def get_redis_pool() -> redis.ConnectionPool:
    """Get or create Redis connection pool."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            decode_responses=True,
        )
    return _redis_pool


async def get_redis_client() -> redis.Redis:
    """Get a Redis client from the pool."""
    pool = await get_redis_pool()
    return redis.Redis(connection_pool=pool)


def get_user_channel(user_id: int) -> str:
    """Get the Redis pub/sub channel name for a user."""
    return f"user:{user_id}:events"


async def event_generator(
    user_id: int,
    request: Request,
) -> AsyncGenerator[str, None]:
    """
    Generate SSE events for a user.

    Listens to Redis pub/sub for events targeted at the user.
    Sends a heartbeat every 30 seconds to keep the connection alive.

    Args:
        user_id: The user's ID to listen for events.
        request: FastAPI request object for disconnect detection.

    Yields:
        SSE formatted event strings.
    """
    client = await get_redis_client()
    pubsub = client.pubsub()
    channel = get_user_channel(user_id)

    try:
        await pubsub.subscribe(channel)
        logger.info(f"User {user_id} subscribed to SSE channel: {channel}")

        # Send initial connection event
        yield format_sse_event("connected", {"status": "connected"})

        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                logger.info(f"User {user_id} disconnected from SSE")
                break

            try:
                # Wait for message with timeout for heartbeat
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=30.0,
                )

                if message is not None and message["type"] == "message":
                    # Parse the message data
                    try:
                        data = json.loads(message["data"])
                        event_type = data.get("event_type", "message")
                        event_data = data.get("data", {})
                        yield format_sse_event(event_type, event_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in SSE message: {message['data']}")
                        continue

            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield format_sse_event("heartbeat", {"status": "alive"})

    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled for user {user_id}")
    except Exception as e:
        logger.error(f"SSE error for user {user_id}: {e}")
        yield format_sse_event("error", {"message": "Connection error"})
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await client.close()
        logger.info(f"User {user_id} unsubscribed from SSE channel: {channel}")


def format_sse_event(event_type: str, data: dict[str, Any]) -> str:
    """
    Format data as an SSE event string.

    Args:
        event_type: The event type name.
        data: The event data to send.

    Returns:
        SSE formatted string with event type included in data.
    """
    event_payload = {
        "type": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    json_data = json.dumps(event_payload)
    return f"data: {json_data}\n\n"


async def get_user_from_token(token: str = Query(..., description="JWT access token")) -> int:
    """
    Validate JWT token from query parameter and return user ID.

    SSE/EventSource cannot send custom headers, so we accept token via query param.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        return int(user_id)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


@router.get("/stream")
async def stream_events(
    request: Request,
    user_id: int = Depends(get_user_from_token),
) -> StreamingResponse:
    """
    Stream Server-Sent Events for the authenticated user.

    Events include:
    - credit_update: When user's credits change
    - generation_update: When a generation status changes
    - character_created: When a new character is created
    - animation_created: When a new animation is created
    - heartbeat: Keep-alive signal every 30 seconds
    - connected: Initial connection confirmation

    Returns:
        StreamingResponse with SSE content type.
    """
    return StreamingResponse(
        event_generator(user_id, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


# Helper functions to publish events from other parts of the app


async def _publish_event(user_id: int, event_type: str, data: dict[str, Any]) -> bool:
    """
    Publish an event to a user's SSE channel.

    Args:
        user_id: The user's ID.
        event_type: The type of event.
        data: The event data.

    Returns:
        True if published successfully, False otherwise.
    """
    try:
        client = await get_redis_client()
        channel = get_user_channel(user_id)
        message = json.dumps({
            "event_type": event_type,
            "data": data,
        })
        await client.publish(channel, message)
        await client.close()
        logger.debug(f"Published {event_type} event to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to publish {event_type} event to user {user_id}: {e}")
        return False


async def publish_credit_update(user_id: int, new_balance: int) -> bool:
    """
    Publish a credit update event to a user.

    Args:
        user_id: The user's ID.
        new_balance: The user's new credit balance.

    Returns:
        True if published successfully, False otherwise.
    """
    return await _publish_event(
        user_id,
        "credit_update",
        {"balance": new_balance},
    )


async def publish_generation_update(
    user_id: int,
    generation_id: int,
    status: str,
    data: dict[str, Any] | None = None,
) -> bool:
    """
    Publish a generation status update event to a user.

    Args:
        user_id: The user's ID.
        generation_id: The generation's ID.
        status: The new status (queued, processing, completed, failed).
        data: Optional additional data (e.g., character_id, error message).

    Returns:
        True if published successfully, False otherwise.
    """
    event_data: dict[str, Any] = {
        "generation_id": generation_id,
        "status": status,
    }
    if data is not None:
        event_data.update(data)

    return await _publish_event(user_id, "generation_update", event_data)


async def publish_character_created(
    user_id: int,
    character_id: int,
    character_data: dict[str, Any],
) -> bool:
    """
    Publish a character created event to a user.

    Args:
        user_id: The user's ID.
        character_id: The new character's ID.
        character_data: Character data to include in the event.

    Returns:
        True if published successfully, False otherwise.
    """
    event_data = {
        "character_id": character_id,
        **character_data,
    }
    return await _publish_event(user_id, "character_created", event_data)


async def publish_animation_created(
    user_id: int,
    animation_id: int,
    animation_data: dict[str, Any],
) -> bool:
    """
    Publish an animation created event to a user.

    Args:
        user_id: The user's ID.
        animation_id: The new animation's ID.
        animation_data: Animation data to include in the event.

    Returns:
        True if published successfully, False otherwise.
    """
    event_data = {
        "animation_id": animation_id,
        **animation_data,
    }
    return await _publish_event(user_id, "animation_created", event_data)
