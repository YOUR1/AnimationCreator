'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Plus, Users, Trash2, X, Loader2 } from 'lucide-react';
import type { Character } from '@/types';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface PendingGeneration {
  id: number;
  type: string;
  status: string;
  credits_used: number;
  created_at: string;
}

export default function CharactersPage() {
  const [characters, setCharacters] = useState<Character[]>([]);
  const [pendingGenerations, setPendingGenerations] = useState<PendingGeneration[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [cancellingId, setCancellingId] = useState<number | null>(null);

  useEffect(() => {
    fetchCharacters();
    fetchPendingGenerations();
  }, []);

  // Poll for pending generation updates
  useEffect(() => {
    if (pendingGenerations.length === 0) return;

    const interval = setInterval(async () => {
      const response = await api.getPendingGenerations();
      const pending = response.generations.filter(g => g.type === 'character');

      // If a generation completed, refresh the characters list
      if (pending.length < pendingGenerations.length) {
        fetchCharacters();
      }

      setPendingGenerations(pending);

      // Stop polling when all generations are done
      if (pending.length === 0) {
        clearInterval(interval);
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [pendingGenerations.length]);

  const fetchCharacters = async () => {
    try {
      const response = await api.getCharacters(1, 50);
      setCharacters(response.items);
    } catch (error) {
      console.error('Failed to fetch characters:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPendingGenerations = async () => {
    try {
      const response = await api.getPendingGenerations();
      setPendingGenerations(response.generations.filter(g => g.type === 'character'));
    } catch (error) {
      console.error('Failed to fetch pending generations:', error);
    }
  };

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
      await api.deleteCharacter(deleteId);
      setCharacters(characters.filter((c) => c.id !== deleteId));
      setDeleteId(null);
    } catch (error) {
      console.error('Failed to delete character:', error);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Characters</h1>
          <p className="text-muted-foreground">Manage your character library</p>
        </div>
        <Link href="/characters/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Character
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
                <CardHeader className="p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-base">Generating...</CardTitle>
                      <p className="text-sm text-muted-foreground">{gen.credits_used} credits</p>
                    </div>
                    {gen.status === 'queued' && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
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
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="aspect-square rounded-lg" />
          ))}
        </div>
      ) : characters.length === 0 && pendingGenerations.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Users className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No characters yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create your first character to start animating
            </p>
            <Link href="/characters/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Character
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {characters.map((character) => (
            <Card key={character.id} className="group overflow-hidden">
              <Link href={`/characters/${character.id}`}>
                <div className="relative aspect-square bg-muted">
                  {character.thumbnail_url || character.image_url ? (
                    <img
                      src={character.thumbnail_url || character.image_url}
                      alt={character.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center">
                      <Users className="h-12 w-12 text-muted-foreground" />
                    </div>
                  )}
                </div>
              </Link>
              <CardHeader className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base truncate">{character.name}</CardTitle>
                    <p className="text-sm text-muted-foreground truncate">
                      {character.style}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                    onClick={(e) => {
                      e.preventDefault();
                      setDeleteId(character.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Character</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this character? This action cannot be undone.
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
    </div>
  );
}
