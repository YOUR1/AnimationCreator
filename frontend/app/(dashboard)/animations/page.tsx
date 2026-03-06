'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Plus, Film, Trash2, Download, Play, X, Loader2, Users } from 'lucide-react';
import type { Animation, Character } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ChromaKeyCanvas } from '@/components/ChromaKeyCanvas';
import { AnimatedThumbnail } from '@/components/AnimatedThumbnail';

interface PendingGeneration {
  id: number;
  type: string;
  status: string;
  credits_used: number;
  created_at: string;
}

interface GroupedAnimations {
  character: Character;
  animations: Animation[];
}

export default function AnimationsPage() {
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [pendingGenerations, setPendingGenerations] = useState<PendingGeneration[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [previewAnimation, setPreviewAnimation] = useState<Animation | null>(null);
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [animResponse, charResponse] = await Promise.all([
        api.getAnimations(1, 100),
        api.getCharacters(1, 100),
      ]);
      setAnimations(animResponse.items);
      setCharacters(charResponse.items);
      fetchPendingGenerations();
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPendingGenerations = async () => {
    try {
      const response = await api.getPendingGenerations();
      setPendingGenerations(response.generations.filter(g => g.type === 'animation'));
    } catch (error) {
      console.error('Failed to fetch pending generations:', error);
    }
  };

  // Group animations by character
  const groupedAnimations = useMemo((): GroupedAnimations[] => {
    const characterMap = new Map<string, Character>();
    characters.forEach(char => characterMap.set(char.id, char));

    const groups = new Map<string, Animation[]>();

    animations.forEach(anim => {
      const charId = anim.character_id;
      if (!groups.has(charId)) {
        groups.set(charId, []);
      }
      groups.get(charId)!.push(anim);
    });

    const result: GroupedAnimations[] = [];
    groups.forEach((anims, charId) => {
      const character = characterMap.get(charId);
      if (character) {
        result.push({
          character,
          animations: anims.sort((a, b) =>
            new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          ),
        });
      }
    });

    // Sort by most recent animation
    return result.sort((a, b) => {
      const aLatest = new Date(a.animations[0]?.created_at || 0).getTime();
      const bLatest = new Date(b.animations[0]?.created_at || 0).getTime();
      return bLatest - aLatest;
    });
  }, [animations, characters]);

  const handleCancelGeneration = async (id: number) => {
    setCancellingId(id);
    try {
      await api.cancelGeneration(id);
      setPendingGenerations(pendingGenerations.filter(g => g.id !== id));
    } catch (error) {
      console.error('Failed to cancel generation:', error);
    } finally {
      setCancellingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deleteId) return;
    setIsDeleting(true);
    try {
      await api.deleteAnimation(deleteId);
      setAnimations(animations.filter((a) => a.id !== deleteId));
      setDeleteId(null);
    } catch (error) {
      console.error('Failed to delete animation:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default">Completed</Badge>;
      case 'processing':
        return <Badge variant="secondary">Processing</Badge>;
      case 'pending':
        return <Badge variant="outline">Pending</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Animations</h1>
          <p className="text-muted-foreground">Manage your animation library</p>
        </div>
        <Link href="/animations/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Animation
          </Button>
        </Link>
      </div>

      {pendingGenerations.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Pending Generations</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {pendingGenerations.map((gen) => (
              <Card key={gen.id} className="overflow-hidden border-dashed">
                <div className="relative aspect-square bg-muted flex items-center justify-center">
                  <div className="text-center p-4">
                    <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground capitalize">{gen.status}</p>
                  </div>
                </div>
                <CardHeader className="p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-sm">Generating...</CardTitle>
                      <p className="text-xs text-muted-foreground">{gen.credits_used} credits</p>
                    </div>
                    {gen.status === 'queued' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 text-muted-foreground hover:text-destructive"
                        onClick={() => handleCancelGeneration(gen.id)}
                        disabled={cancellingId === gen.id}
                      >
                        {cancellingId === gen.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <X className="h-4 w-4" />
                        )}
                      </Button>
                    )}
                  </div>
                </CardHeader>
              </Card>
            ))}
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-6">
          {[...Array(2)].map((_, i) => (
            <div key={i} className="space-y-3">
              <Skeleton className="h-8 w-48" />
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {[...Array(4)].map((_, j) => (
                  <Skeleton key={j} className="aspect-square rounded-lg" />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : groupedAnimations.length === 0 && pendingGenerations.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Film className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No animations yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create your first animation from a character
            </p>
            <Link href="/animations/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Animation
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-8">
          {groupedAnimations.map(({ character, animations: charAnimations }) => (
            <div key={character.id} className="space-y-4">
              {/* Character Header */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full overflow-hidden bg-muted flex-shrink-0">
                  {character.thumbnail_url || character.image_url ? (
                    <img
                      src={character.thumbnail_url || character.image_url}
                      alt={character.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Users className="h-5 w-5 text-muted-foreground" />
                    </div>
                  )}
                </div>
                <div>
                  <h2 className="text-lg font-semibold">{character.name}</h2>
                  <p className="text-sm text-muted-foreground">
                    {charAnimations.length} animation{charAnimations.length !== 1 ? 's' : ''}
                  </p>
                </div>
              </div>

              {/* Animations Grid */}
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                {charAnimations.map((animation) => (
                  <Card key={animation.id} className="group overflow-hidden">
                    <div className="relative aspect-square">
                      <AnimatedThumbnail
                        gifUrl={animation.gif_url}
                        videoUrl={animation.video_url}
                        thumbnailUrl={animation.thumbnail_url}
                        alt={animation.name}
                        onClick={() => animation.status === 'completed' && setPreviewAnimation(animation)}
                      />
                      {animation.status === 'completed' && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                          <Play className="h-10 w-10 text-white" />
                        </div>
                      )}
                    </div>
                    <CardHeader className="p-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <CardTitle className="text-sm truncate capitalize">
                            {animation.type || animation.name}
                          </CardTitle>
                          <div className="flex items-center gap-2 mt-1">
                            {getStatusBadge(animation.status)}
                          </div>
                        </div>
                        <div className="flex gap-1 flex-shrink-0">
                          {animation.status === 'completed' && animation.video_url && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              asChild
                            >
                              <a href={animation.video_url} download>
                                <Download className="h-3.5 w-3.5" />
                              </a>
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              setDeleteId(animation.id);
                            }}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </div>
                    </CardHeader>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Dialog */}
      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Animation</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this animation? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>
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

      {/* Preview Dialog with Chroma Key */}
      <Dialog open={!!previewAnimation} onOpenChange={() => setPreviewAnimation(null)}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle className="capitalize">
              {previewAnimation?.type || previewAnimation?.name}
            </DialogTitle>
            <DialogDescription>
              Green screen removed preview. Click to play/pause.
            </DialogDescription>
          </DialogHeader>
          {(previewAnimation?.gif_url || previewAnimation?.video_url) && (
            <div className="aspect-square max-h-[70vh] mx-auto bg-muted rounded-lg overflow-hidden">
              <ChromaKeyCanvas
                key={previewAnimation.id}
                gifUrl={previewAnimation.gif_url}
                videoUrl={previewAnimation.video_url}
                className="w-full h-full"
                tolerance={120}
                background="transparent"
              />
            </div>
          )}
          <div className="flex justify-center gap-2 mt-2">
            {previewAnimation?.video_url && (
              <Button variant="outline" size="sm" asChild>
                <a href={previewAnimation.video_url} download>
                  <Download className="h-4 w-4 mr-2" />
                  Download Video
                </a>
              </Button>
            )}
            {previewAnimation?.gif_url && (
              <Button variant="outline" size="sm" asChild>
                <a href={previewAnimation.gif_url} download>
                  <Download className="h-4 w-4 mr-2" />
                  Download GIF
                </a>
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
