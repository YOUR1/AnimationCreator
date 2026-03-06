#!/bin/bash

# Single-command development startup
# Runs everything with hot-reload

set -e

cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID $CELERY_PID 2>/dev/null
    docker-compose -f docker-compose.dev.yml down
    exit 0
}

trap cleanup SIGINT SIGTERM

echo -e "${GREEN}Starting AnimationCreator Dev Environment${NC}"
echo "==========================================="

# Export env vars
set -a
source .env.local
set +a

# Start infrastructure
echo -e "${GREEN}Starting PostgreSQL (5433) + Redis (6380)...${NC}"
docker-compose -f docker-compose.dev.yml up -d

# Wait for db
echo "Waiting for database..."
sleep 3

# Activate Python virtual environment
source venv/bin/activate

# Set Python path to include root (for animation_creator) and backend
export PYTHONPATH="$(pwd):$(pwd)/backend:$PYTHONPATH"

# Install dependencies if needed
if [ "$1" == "--install" ] || [ ! -d "frontend/node_modules" ]; then
    echo -e "${GREEN}Installing frontend dependencies...${NC}"
    cd frontend && npm install && cd ..
fi

if [ "$1" == "--install" ]; then
    echo -e "${GREEN}Installing Python dependencies...${NC}"
    pip install -r requirements.txt -q
    pip install -r backend/requirements.txt -q
fi

# Start backend
echo -e "${GREEN}Starting backend (3131)...${NC}"
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 3131 &
BACKEND_PID=$!
cd ..

# Start celery
echo -e "${GREEN}Starting Celery worker...${NC}"
cd backend
celery -A app.core.celery_config worker --loglevel=info -Q character,animation,video,gif &
CELERY_PID=$!
cd ..

# Start frontend
echo -e "${GREEN}Starting frontend (3000)...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${GREEN}All services running!${NC}"
echo "  Frontend: http://localhost:3000"
echo "  Backend:  http://localhost:3131"
echo "  DB:       localhost:5433"
echo "  Redis:    localhost:6380"
echo ""
echo "Press Ctrl+C to stop all services"

wait
