'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/contexts/auth-context';
import api from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, Film, CreditCard, Plus, ArrowRight } from 'lucide-react';
import { AnimatedThumbnail } from '@/components/AnimatedThumbnail';
import type { Character, Animation, PaginatedResponse } from '@/types';

export default function DashboardPage() {
  const { user, credits } = useAuth();
  const [characters, setCharacters] = useState<Character[]>([]);
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [charResponse, animResponse] = await Promise.all([
          api.getCharacters(1, 4),
          api.getAnimations(1, 4),
        ]);
        setCharacters(charResponse.items);
        setAnimations(animResponse.items);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Welcome back, {user?.name || 'Creator'}!</h1>
        <p className="text-muted-foreground mt-1">
          Here's an overview of your animation studio
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Characters</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{characters.length}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Animations</CardTitle>
            <Film className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{animations.length}</div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Credits</CardTitle>
            <CreditCard className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{credits?.credits ?? 0}</div>
            <Link href="/billing" className="text-xs text-primary hover:underline">
              Buy more credits
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Create Character</CardTitle>
            <CardDescription>
              Generate a new character to animate
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/characters/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Character
              </Button>
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Create Animation</CardTitle>
            <CardDescription>
              Bring your characters to life
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/animations/new">
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                New Animation
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Recent Characters */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Characters</CardTitle>
            <CardDescription>Your latest character creations</CardDescription>
          </div>
          <Link href="/characters">
            <Button variant="ghost" size="sm">
              View all <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="aspect-square rounded-lg" />
              ))}
            </div>
          ) : characters.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No characters yet. Create your first one!
            </p>
          ) : (
            <div className="grid gap-4 md:grid-cols-4">
              {characters.map((character) => (
                <Link key={character.id} href={`/characters/${character.id}`}>
                  <div className="group relative aspect-square rounded-lg overflow-hidden bg-muted">
                    {character.thumbnail_url || character.image_url ? (
                      <img
                        src={character.thumbnail_url || character.image_url}
                        alt={character.name}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <Users className="h-8 w-8 text-muted-foreground" />
                      </div>
                    )}
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-3">
                      <p className="text-white text-sm font-medium truncate">
                        {character.name}
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Animations */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Animations</CardTitle>
            <CardDescription>Your latest animation creations</CardDescription>
          </div>
          <Link href="/animations">
            <Button variant="ghost" size="sm">
              View all <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </Link>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid gap-4 md:grid-cols-4">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="aspect-square rounded-lg" />
              ))}
            </div>
          ) : animations.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No animations yet. Create your first one!
            </p>
          ) : (
            <div className="grid gap-4 md:grid-cols-4">
              {animations.map((animation) => (
                <Link key={animation.id} href={`/animations/${animation.id}`}>
                  <div className="group relative aspect-square rounded-lg overflow-hidden">
                    <AnimatedThumbnail
                      gifUrl={animation.gif_url}
                      videoUrl={animation.video_url}
                      thumbnailUrl={animation.thumbnail_url}
                      alt={animation.name}
                    />
                    <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/60 to-transparent p-3 pointer-events-none">
                      <p className="text-white text-sm font-medium truncate">
                        {animation.name}
                      </p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
