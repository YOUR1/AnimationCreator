'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface CharacterPreviewProps {
  imageUrl?: string | null;
  name?: string;
  isLoading?: boolean;
  className?: string;
  onImageError?: () => void;
}

export function CharacterPreview({
  imageUrl,
  name = 'Character',
  isLoading = false,
  className,
  onImageError,
}: CharacterPreviewProps) {
  const [zoom, setZoom] = useState(1);
  const [imageError, setImageError] = useState(false);

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.25, 2));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.25, 0.5));
  const handleReset = () => setZoom(1);

  const handleImageError = () => {
    setImageError(true);
    onImageError?.();
  };

  if (isLoading) {
    return (
      <Card className={cn('overflow-hidden', className)}>
        <CardContent className="p-0">
          <div className="aspect-square relative">
            <Skeleton className="absolute inset-0" />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-pulse text-muted-foreground">
                  Generating...
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!imageUrl || imageError) {
    return (
      <Card className={cn('overflow-hidden', className)}>
        <CardContent className="p-0">
          <div className="aspect-square relative bg-muted flex items-center justify-center">
            <div className="text-center text-muted-foreground">
              <p>No preview available</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('overflow-hidden', className)}>
      <CardContent className="p-0">
        <div className="aspect-square relative overflow-hidden bg-muted">
          <div
            className="absolute inset-0 flex items-center justify-center transition-transform duration-200"
            style={{ transform: `scale(${zoom})` }}
          >
            <img
              src={imageUrl}
              alt={name}
              className="w-full h-full object-contain"
              onError={handleImageError}
            />
          </div>
          <div className="absolute bottom-2 right-2 flex gap-1">
            <Button
              variant="secondary"
              size="icon"
              className="h-8 w-8 opacity-80 hover:opacity-100"
              onClick={handleZoomOut}
              disabled={zoom <= 0.5}
            >
              <ZoomOut className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              className="h-8 w-8 opacity-80 hover:opacity-100"
              onClick={handleReset}
            >
              <RotateCcw className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              className="h-8 w-8 opacity-80 hover:opacity-100"
              onClick={handleZoomIn}
              disabled={zoom >= 2}
            >
              <ZoomIn className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
