'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { CharacterPreview } from '@/components/creator/CharacterPreview';
import { AnimationGallery } from '@/components/creator/AnimationGallery';
import { DownloadButton } from '@/components/creator/DownloadButton';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ArrowLeft, Trash2, Play, Calendar, Palette, FileText } from 'lucide-react';
import type { Character, Animation } from '@/types';

export default function CharacterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const characterId = params.id as string;

  const [character, setCharacter] = useState<Character | null>(null);
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingAnimations, setIsLoadingAnimations] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    fetchCharacter();
    fetchAnimations();
  }, [characterId]);

  const fetchCharacter = async () => {
    try {
      const data = await api.getCharacter(characterId);
      setCharacter(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load character');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAnimations = async () => {
    try {
      const response = await api.getAnimations(1, 50, { characterId });
      setAnimations(response.items);
    } catch (err) {
      console.error('Failed to fetch animations:', err);
    } finally {
      setIsLoadingAnimations(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await api.deleteCharacter(characterId);
      router.push('/characters');
    } catch (err) {
      console.error('Failed to delete character:', err);
      setIsDeleting(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <div className="grid gap-6 lg:grid-cols-2">
          <Skeleton className="aspect-square rounded-lg" />
          <div className="space-y-4">
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-24 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !character) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Link href="/characters">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">Character Not Found</h1>
            <p className="text-muted-foreground">{error || 'The character you are looking for does not exist.'}</p>
          </div>
        </div>
        <Link href="/characters">
          <Button>Back to Characters</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/characters">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <h1 className="text-3xl font-bold">{character.name}</h1>
            <p className="text-muted-foreground">Character details and animations</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {character.image_url && (
            <DownloadButton
              url={character.image_url}
              filename={`${character.name}.png`}
              variant="outline"
            />
          )}
          <Button
            variant="destructive"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Character Preview */}
        <CharacterPreview
          imageUrl={character.image_url}
          name={character.name}
        />

        {/* Character Details */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Character Information</CardTitle>
              <CardDescription>Details about this character</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {character.style && (
                <div className="flex items-start gap-3">
                  <Palette className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">Art Style</p>
                    <Badge variant="secondary" className="mt-1">
                      {character.style}
                    </Badge>
                  </div>
                </div>
              )}

              {character.prompt && (
                <div className="flex items-start gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">Description</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {character.prompt}
                    </p>
                  </div>
                </div>
              )}

              {character.description && (
                <div className="flex items-start gap-3">
                  <FileText className="h-5 w-5 text-muted-foreground mt-0.5" />
                  <div>
                    <p className="text-sm font-medium">Notes</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {character.description}
                    </p>
                  </div>
                </div>
              )}

              <div className="flex items-start gap-3">
                <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                <div>
                  <p className="text-sm font-medium">Created</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {formatDate(character.created_at)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Generate Animation CTA */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">Create Animation</h3>
                  <p className="text-sm text-muted-foreground">
                    Generate new animations with this character
                  </p>
                </div>
                <Link href={`/animations/new?character=${characterId}`}>
                  <Button>
                    <Play className="h-4 w-4 mr-2" />
                    Animate
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Animations Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">Animations</h2>
            <p className="text-muted-foreground">
              {animations.length} animation{animations.length !== 1 ? 's' : ''} created with this character
            </p>
          </div>
          <Link href={`/animations/new?character=${characterId}`}>
            <Button variant="outline">
              <Play className="h-4 w-4 mr-2" />
              New Animation
            </Button>
          </Link>
        </div>

        <AnimationGallery
          animations={animations}
          isLoading={isLoadingAnimations}
          showControls
        />
      </div>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Character</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{character.name}"? This will also delete all associated animations. This action cannot be undone.
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
