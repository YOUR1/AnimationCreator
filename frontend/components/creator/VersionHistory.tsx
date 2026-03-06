'use client';

import { useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Clock, Check, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface Version {
  id: string;
  imageUrl: string;
  thumbnailUrl?: string;
  createdAt: string;
  isActive?: boolean;
  status?: 'completed' | 'failed' | 'processing';
}

interface VersionHistoryProps {
  versions: Version[];
  currentVersionId?: string;
  onSelectVersion: (version: Version) => void;
  isLoading?: boolean;
  className?: string;
}

export function VersionHistory({
  versions,
  currentVersionId,
  onSelectVersion,
  isLoading = false,
  className,
}: VersionHistoryProps) {
  const [selectedId, setSelectedId] = useState<string | undefined>(currentVersionId);

  const handleSelect = (version: Version) => {
    setSelectedId(version.id);
    onSelectVersion(version);
  };

  if (isLoading) {
    return (
      <Card className={cn('', className)}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Version History</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-16 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (versions.length === 0) {
    return (
      <Card className={cn('', className)}>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Version History</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No versions yet</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn('', className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Clock className="h-4 w-4" />
          Version History
          <Badge variant="secondary" className="ml-auto">
            {versions.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <ScrollArea className="h-[300px]">
          <div className="space-y-1 p-4 pt-0">
            {versions.map((version, index) => {
              const isSelected = version.id === selectedId;
              const isCurrentVersion = version.id === currentVersionId;
              const timeAgo = formatDistanceToNow(new Date(version.createdAt), {
                addSuffix: true,
              });

              return (
                <Button
                  key={version.id}
                  variant="ghost"
                  className={cn(
                    'w-full justify-start h-auto p-2 hover:bg-accent',
                    isSelected && 'bg-accent'
                  )}
                  onClick={() => handleSelect(version)}
                >
                  <div className="flex items-center gap-3 w-full">
                    <div className="relative h-12 w-12 rounded overflow-hidden bg-muted flex-shrink-0">
                      {version.thumbnailUrl || version.imageUrl ? (
                        <img
                          src={version.thumbnailUrl || version.imageUrl}
                          alt={`Version ${versions.length - index}`}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full bg-muted" />
                      )}
                    </div>
                    <div className="flex-1 text-left">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">
                          Version {versions.length - index}
                        </span>
                        {isCurrentVersion && (
                          <Badge variant="default" className="h-5 text-xs">
                            <Check className="h-3 w-3 mr-1" />
                            Current
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{timeAgo}</p>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </Button>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
