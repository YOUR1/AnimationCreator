'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Trash2, AlertCircle, User, Calendar, Clock, Film } from 'lucide-react';
import { VideoPlayer } from '@/components/creator/VideoPlayer';
import { DownloadButton } from '@/components/creator/DownloadButton';
import { JobStatusBadge } from '@/components/creator/JobStatusBadge';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { Animation, Character, GenerationStatus } from '@/types';

export default function AnimationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const animationId = params.id as string;

  const [animation, setAnimation] = useState<Animation | null>(null);
  const [character, setCharacter] = useState<Character | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const fetchAnimation = async () => {
      try {
        const data = await api.getAnimation(animationId);
        setAnimation(data);

        // Fetch the parent character
        if (data.character_id) {
          try {
            const characterData = await api.getCharacter(data.character_id);
            setCharacter(characterData);
          } catch (err) {
            console.error('Failed to fetch character:', err);
          }
        }
      } catch (err) {
        setError('Failed to load animation');
        console.error('Failed to fetch animation:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchAnimation();
  }, [animationId]);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteAnimation(animationId);
      router.push('/animations');
    } catch (err) {
      console.error('Failed to delete animation:', err);
      setIsDeleting(false);
      setShowDeleteDialog(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Skeleton className="aspect-video w-full rounded-lg" />
        <div className="grid gap-4 md:grid-cols-2">
          <Skeleton className="h-32" />
          <Skeleton className="h-32" />
        </div>
      </div>
    );
  }

  if (error || !animation) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Animation not found</h3>
            <p className="text-muted-foreground text-center mb-4">
              The animation you're looking for doesn't exist or has been deleted
            </p>
            <Link href="/animations">
              <Button>Back to Animations</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/animations">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold">{animation.name}</h1>
              <JobStatusBadge status={animation.status as GenerationStatus} />
            </div>
            <p className="text-muted-foreground">
              {animation.type.charAt(0).toUpperCase() + animation.type.slice(1)} animation
            </p>
          </div>
        </div>
        <Button
          variant="outline"
          size="icon"
          className="text-muted-foreground hover:text-destructive"
          onClick={() => setShowDeleteDialog(true)}
        >
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Video Player */}
      {animation.status === 'completed' && animation.video_url && (
        <Card className="overflow-hidden">
          <CardContent className="p-0">
            <VideoPlayer
              src={animation.video_url}
              poster={animation.thumbnail_url}
              className="aspect-video"
              loop
            />
          </CardContent>
        </Card>
      )}

      {/* Processing/Pending State */}
      {(animation.status === 'pending' || animation.status === 'processing') && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Film className="h-12 w-12 text-muted-foreground mb-4 animate-pulse" />
            <h3 className="text-lg font-semibold mb-2">
              {animation.status === 'pending' ? 'Waiting to process' : 'Processing animation'}
            </h3>
            <p className="text-muted-foreground text-center">
              {animation.status === 'pending'
                ? 'Your animation is queued and will start processing soon'
                : 'Your animation is being generated. This may take a few minutes.'}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Failed State */}
      {animation.status === 'failed' && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <AlertCircle className="h-12 w-12 text-destructive mb-4" />
            <h3 className="text-lg font-semibold mb-2">Generation failed</h3>
            <p className="text-muted-foreground text-center mb-4">
              Something went wrong while generating this animation
            </p>
            <Link href="/animations/new">
              <Button>Try Again</Button>
            </Link>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        {/* Animation Details */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Animation Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                <Film className="h-4 w-4 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">Type</p>
                <p className="text-sm text-muted-foreground">
                  {animation.type.charAt(0).toUpperCase() + animation.type.slice(1)}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                <Clock className="h-4 w-4 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">Duration</p>
                <p className="text-sm text-muted-foreground">
                  {animation.duration ? `${animation.duration} seconds` : 'N/A'}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                <Calendar className="h-4 w-4 text-muted-foreground" />
              </div>
              <div>
                <p className="text-sm font-medium">Created</p>
                <p className="text-sm text-muted-foreground">
                  {formatDate(animation.created_at)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Parent Character */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Character</CardTitle>
          </CardHeader>
          <CardContent>
            {character ? (
              <Link href={`/characters`} className="block">
                <div className="flex items-center gap-4 p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                  <div className="relative h-16 w-16 rounded-lg overflow-hidden bg-muted flex-shrink-0">
                    {character.thumbnail_url || character.image_url ? (
                      <img
                        src={character.thumbnail_url || character.image_url}
                        alt={character.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <User className="h-6 w-6 text-muted-foreground" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{character.name}</p>
                    {character.style && (
                      <p className="text-sm text-muted-foreground truncate">
                        {character.style}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            ) : (
              <div className="flex items-center gap-4 p-3 rounded-lg border">
                <div className="h-16 w-16 rounded-lg bg-muted flex items-center justify-center flex-shrink-0">
                  <User className="h-6 w-6 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">
                    Character not available
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Download Section */}
      {animation.status === 'completed' && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Downloads</CardTitle>
            <CardDescription>Download your animation in available formats</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {animation.video_url && (
                <DownloadButton
                  url={animation.video_url}
                  filename={`${animation.name}.mp4`}
                >
                  Download Video
                </DownloadButton>
              )}
              {animation.thumbnail_url && (
                <DownloadButton
                  url={animation.thumbnail_url}
                  filename={`${animation.name}-thumbnail.png`}
                  variant="secondary"
                >
                  Download Thumbnail
                </DownloadButton>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Animation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{animation.name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
