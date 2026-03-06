'use client';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DownloadButton } from './DownloadButton';
import { JobStatusBadge } from './JobStatusBadge';
import { AnimatedThumbnail } from '@/components/AnimatedThumbnail';
import { Play, Clock } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Animation } from '@/types';

interface AnimationGalleryProps {
  animations: Animation[];
  isLoading?: boolean;
  onSelect?: (animation: Animation) => void;
  selectedId?: string;
  showControls?: boolean;
  className?: string;
}

export function AnimationGallery({
  animations,
  isLoading = false,
  onSelect,
  selectedId,
  showControls = true,
  className,
}: AnimationGalleryProps) {
  // Removed playingId state - using AnimatedThumbnail for hover playback

  if (isLoading) {
    return (
      <div className={cn('grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4', className)}>
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="overflow-hidden">
            <Skeleton className="aspect-square" />
            <CardContent className="p-3">
              <Skeleton className="h-4 w-3/4 mb-2" />
              <Skeleton className="h-3 w-1/2" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (animations.length === 0) {
    return (
      <Card className={cn('', className)}>
        <CardContent className="flex flex-col items-center justify-center py-16">
          <Play className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">No animations yet</h3>
          <p className="text-muted-foreground text-center">
            Generated animations will appear here
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className={cn('grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4', className)}>
      {animations.map((animation) => {
        const isSelected = animation.id === selectedId;

        return (
          <Card
            key={animation.id}
            className={cn(
              'overflow-hidden cursor-pointer transition-all hover:ring-2 hover:ring-primary/50',
              isSelected && 'ring-2 ring-primary'
            )}
            onClick={() => onSelect?.(animation)}
          >
            <div className="aspect-square relative">
              {animation.status === 'completed' ? (
                <AnimatedThumbnail
                  gifUrl={animation.gif_url}
                  videoUrl={animation.video_url}
                  thumbnailUrl={animation.thumbnail_url}
                  alt={animation.name}
                />
              ) : animation.status === 'processing' ? (
                <div className="w-full h-full flex items-center justify-center bg-muted">
                  <div className="text-center">
                    <div className="animate-pulse mb-2">
                      <Play className="h-8 w-8 text-muted-foreground mx-auto" />
                    </div>
                    <span className="text-sm text-muted-foreground">Processing...</span>
                  </div>
                </div>
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-muted">
                  <Clock className="h-8 w-8 text-muted-foreground" />
                </div>
              )}

              <div className="absolute top-2 right-2">
                <JobStatusBadge status={animation.status} showIcon={false} />
              </div>
            </div>

            <CardContent className="p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-sm truncate">{animation.name}</h4>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="outline" className="text-xs">
                      {animation.type}
                    </Badge>
                    {animation.duration && (
                      <span className="text-xs text-muted-foreground">
                        {animation.duration}s
                      </span>
                    )}
                  </div>
                </div>
                {showControls && animation.status === 'completed' && animation.video_url && (
                  <DownloadButton
                    url={animation.video_url}
                    filename={`${animation.name}.mp4`}
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                  />
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
