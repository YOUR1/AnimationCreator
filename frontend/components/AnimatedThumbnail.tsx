'use client';

import { useState } from 'react';
import { Film } from 'lucide-react';
import { cn } from '@/lib/utils';

interface AnimatedThumbnailProps {
  /** GIF URL (preferred - will animate) */
  gifUrl?: string;
  /** Video URL (fallback) */
  videoUrl?: string;
  /** Static thumbnail URL (shown when not hovering, if playOnHover is true) */
  thumbnailUrl?: string;
  /** Alt text for accessibility */
  alt?: string;
  /** Additional CSS classes */
  className?: string;
  /** Whether to only play on hover (default: false - always plays) */
  playOnHover?: boolean;
  /** Click handler */
  onClick?: () => void;
}

export function AnimatedThumbnail({
  gifUrl,
  videoUrl,
  thumbnailUrl,
  alt = 'Animation',
  className,
  playOnHover = false,
  onClick,
}: AnimatedThumbnailProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  const shouldAnimate = !playOnHover || isHovered;
  const showGif = gifUrl && shouldAnimate;
  const showVideo = !gifUrl && videoUrl;

  // Determine what to show
  const showStatic = playOnHover && !isHovered && thumbnailUrl;

  return (
    <div
      className={cn(
        'relative w-full h-full bg-muted overflow-hidden',
        onClick && 'cursor-pointer',
        className
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={onClick}
    >
      {/* Checkerboard background for transparency */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage: `
            linear-gradient(45deg, #e5e5e5 25%, transparent 25%),
            linear-gradient(-45deg, #e5e5e5 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, #e5e5e5 75%),
            linear-gradient(-45deg, transparent 75%, #e5e5e5 75%)
          `,
          backgroundSize: '16px 16px',
          backgroundPosition: '0 0, 0 8px, 8px -8px, -8px 0px',
          backgroundColor: '#fff',
        }}
      />

      {/* Static thumbnail (shown when playOnHover and not hovering) */}
      {showStatic && (
        <img
          src={thumbnailUrl}
          alt={alt}
          className="absolute inset-0 w-full h-full object-contain"
        />
      )}

      {/* Animated GIF */}
      {showGif && !hasError && (
        <img
          src={gifUrl}
          alt={alt}
          className="absolute inset-0 w-full h-full object-contain"
          onLoad={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
        />
      )}

      {/* Video fallback */}
      {showVideo && !showStatic && (
        <video
          src={videoUrl}
          className="absolute inset-0 w-full h-full object-contain"
          muted
          loop
          playsInline
          autoPlay={!playOnHover}
          ref={(el) => {
            if (el) {
              if (shouldAnimate) {
                el.play().catch(() => {});
              } else {
                el.pause();
                el.currentTime = 0;
              }
            }
          }}
          onLoadedData={() => setIsLoaded(true)}
          onError={() => setHasError(true)}
        />
      )}

      {/* Fallback icon when no media */}
      {!gifUrl && !videoUrl && !thumbnailUrl && (
        <div className="absolute inset-0 flex items-center justify-center">
          <Film className="h-10 w-10 text-muted-foreground" />
        </div>
      )}

      {/* Error state */}
      {hasError && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted">
          <Film className="h-10 w-10 text-muted-foreground" />
        </div>
      )}
    </div>
  );
}

export default AnimatedThumbnail;
