'use client';

import { useEffect, useRef, useState } from 'react';

interface ChromaKeyCanvasProps {
  /** GIF URL to display (already has transparency from backend) */
  gifUrl?: string;
  /** Video URL fallback (needs chroma key applied) */
  videoUrl?: string;
  className?: string;
  /** Green screen color tolerance (0-255). Higher = more green removed */
  tolerance?: number;
  /** Background color/pattern. 'transparent' for checkerboard */
  background?: 'transparent' | 'white' | 'black' | string;
}

export function ChromaKeyCanvas({
  gifUrl,
  videoUrl,
  className = '',
  tolerance = 100,
  background = 'transparent',
}: ChromaKeyCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const animationRef = useRef<number>();

  // For videos, use canvas with chroma key removal
  useEffect(() => {
    // Skip if we have a GIF (handled by img tag)
    if (gifUrl) return;

    const canvas = canvasRef.current;
    if (!canvas || !videoUrl) return;

    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    if (!ctx) return;

    const video = document.createElement('video');
    video.crossOrigin = 'anonymous';
    video.muted = true;
    video.loop = true;
    video.playsInline = true;

    video.onloadeddata = () => {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      setIsLoaded(true);

      video.play().catch(() => {});

      const animate = () => {
        if (video.paused || video.ended) {
          animationRef.current = requestAnimationFrame(animate);
          return;
        }

        // Draw checkerboard background
        if (background === 'transparent') {
          drawCheckerboard(ctx, canvas.width, canvas.height);
        } else {
          ctx.fillStyle = background;
          ctx.fillRect(0, 0, canvas.width, canvas.height);
        }

        // Draw video frame
        ctx.drawImage(video, 0, 0);

        // Apply chroma key
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        applyChromaKey(imageData.data, tolerance);
        ctx.putImageData(imageData, 0, 0);

        animationRef.current = requestAnimationFrame(animate);
      };

      animationRef.current = requestAnimationFrame(animate);
    };

    video.onerror = () => {
      setError('Failed to load video');
      setIsLoaded(true);
    };

    video.src = videoUrl;

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      video.pause();
      video.src = '';
    };
  }, [gifUrl, videoUrl, tolerance, background]);

  // GIFs from the backend already have transparency applied
  // Display them directly in an img tag which animates natively
  if (gifUrl) {
    return (
      <div className={`relative ${className}`}>
        {background === 'transparent' && (
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: `
                linear-gradient(45deg, #ccc 25%, transparent 25%),
                linear-gradient(-45deg, #ccc 25%, transparent 25%),
                linear-gradient(45deg, transparent 75%, #ccc 75%),
                linear-gradient(-45deg, transparent 75%, #ccc 75%)
              `,
              backgroundSize: '20px 20px',
              backgroundPosition: '0 0, 0 10px, 10px -10px, -10px 0px',
              backgroundColor: '#fff',
            }}
          />
        )}
        <img
          src={gifUrl}
          alt="Animation"
          className="relative w-full h-full object-contain"
          onLoad={() => setIsLoaded(true)}
          onError={() => setError('Failed to load GIF')}
        />
        {!isLoaded && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          </div>
        )}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted">
            <p className="text-destructive text-sm">{error}</p>
          </div>
        )}
      </div>
    );
  }

  // Video canvas fallback
  return (
    <div className={`relative ${className}`}>
      <canvas
        ref={canvasRef}
        className="w-full h-full object-contain"
      />

      {!isLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      )}

      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-muted">
          <p className="text-destructive text-sm">{error}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Apply chroma key (green screen removal) to image data
 */
function applyChromaKey(data: Uint8ClampedArray, tolerance: number) {
  for (let i = 0; i < data.length; i += 4) {
    const r = data[i];
    const g = data[i + 1];
    const b = data[i + 2];

    // Check if pixel is "green enough" to be removed
    // Green should be significantly higher than red and blue
    const isGreen = g > 80 && g > r * 1.2 && g > b * 1.2;

    // Calculate how "green" this pixel is (0-255)
    const greenness = isGreen ? Math.min(255, (g - Math.max(r, b)) * 2) : 0;

    if (greenness > tolerance * 0.5) {
      // Make pixel transparent based on greenness
      const alpha = Math.max(0, 255 - greenness * (255 / tolerance));
      data[i + 3] = alpha;
    }
  }
}

/**
 * Draw checkerboard pattern for transparency visualization
 */
function drawCheckerboard(ctx: CanvasRenderingContext2D, width: number, height: number) {
  const size = 10;
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = '#cccccc';

  for (let y = 0; y < height; y += size) {
    for (let x = 0; x < width; x += size) {
      if ((Math.floor(x / size) + Math.floor(y / size)) % 2 === 0) {
        ctx.fillRect(x, y, size, size);
      }
    }
  }
}

export default ChromaKeyCanvas;
