'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import Link from 'next/link';
import api from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Users, Film, Plus, Search, SlidersHorizontal, Loader2 } from 'lucide-react';
import type { Character, Animation, PaginatedResponse } from '@/types';

const STYLES = [
  { value: 'all', label: 'All Styles' },
  { value: 'kawaii', label: 'Kawaii' },
  { value: 'pixar', label: 'Pixar' },
  { value: 'realistic', label: 'Realistic' },
  { value: 'pixel', label: 'Pixel Art' },
  { value: 'watercolor', label: 'Watercolor' },
];

const ANIMATION_TYPES = [
  { value: 'all', label: 'All Types' },
  { value: 'idle', label: 'Idle' },
  { value: 'walk', label: 'Walk' },
  { value: 'run', label: 'Run' },
  { value: 'jump', label: 'Jump' },
  { value: 'attack', label: 'Attack' },
  { value: 'custom', label: 'Custom' },
];

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest First' },
  { value: 'oldest', label: 'Oldest First' },
];

const PAGE_SIZE = 12;

export default function GalleryPage() {
  // Characters state
  const [characters, setCharacters] = useState<Character[]>([]);
  const [isLoadingCharacters, setIsLoadingCharacters] = useState(true);
  const [isLoadingMoreCharacters, setIsLoadingMoreCharacters] = useState(false);
  const [characterPage, setCharacterPage] = useState(1);
  const [characterTotalPages, setCharacterTotalPages] = useState(1);
  const [characterSearch, setCharacterSearch] = useState('');
  const [characterStyle, setCharacterStyle] = useState('all');
  const [characterSort, setCharacterSort] = useState('newest');

  // Animations state
  const [animations, setAnimations] = useState<Animation[]>([]);
  const [isLoadingAnimations, setIsLoadingAnimations] = useState(true);
  const [isLoadingMoreAnimations, setIsLoadingMoreAnimations] = useState(false);
  const [animationPage, setAnimationPage] = useState(1);
  const [animationTotalPages, setAnimationTotalPages] = useState(1);
  const [animationSearch, setAnimationSearch] = useState('');
  const [animationType, setAnimationType] = useState('all');
  const [animationSort, setAnimationSort] = useState('newest');

  // Fetch characters
  const fetchCharacters = useCallback(async (page: number, append = false) => {
    if (append) {
      setIsLoadingMoreCharacters(true);
    } else {
      setIsLoadingCharacters(true);
    }
    try {
      const response: PaginatedResponse<Character> = await api.getCharacters(page, PAGE_SIZE, {
        sortBy: 'created_at',
        sortOrder: characterSort === 'newest' ? 'desc' : 'asc',
        style: characterStyle !== 'all' ? characterStyle : undefined,
      });
      if (append) {
        setCharacters((prev) => [...prev, ...response.items]);
      } else {
        setCharacters(response.items);
      }
      setCharacterTotalPages(response.total_pages);
    } catch (error) {
      console.error('Failed to fetch characters:', error);
    } finally {
      setIsLoadingCharacters(false);
      setIsLoadingMoreCharacters(false);
    }
  }, [characterSort, characterStyle]);

  // Fetch animations
  const fetchAnimations = useCallback(async (page: number, append = false) => {
    if (append) {
      setIsLoadingMoreAnimations(true);
    } else {
      setIsLoadingAnimations(true);
    }
    try {
      const response: PaginatedResponse<Animation> = await api.getAnimations(page, PAGE_SIZE, {
        sortBy: 'created_at',
        sortOrder: animationSort === 'newest' ? 'desc' : 'asc',
        type: animationType !== 'all' ? animationType : undefined,
      });
      if (append) {
        setAnimations((prev) => [...prev, ...response.items]);
      } else {
        setAnimations(response.items);
      }
      setAnimationTotalPages(response.total_pages);
    } catch (error) {
      console.error('Failed to fetch animations:', error);
    } finally {
      setIsLoadingAnimations(false);
      setIsLoadingMoreAnimations(false);
    }
  }, [animationSort, animationType]);

  // Initial fetch and refetch when filters change
  useEffect(() => {
    setCharacterPage(1);
    fetchCharacters(1);
  }, [fetchCharacters]);

  useEffect(() => {
    setAnimationPage(1);
    fetchAnimations(1);
  }, [fetchAnimations]);

  // Client-side search filtering
  const filteredCharacters = useMemo(() => {
    if (!characterSearch.trim()) return characters;
    const search = characterSearch.toLowerCase();
    return characters.filter(
      (c) =>
        c.name.toLowerCase().includes(search) ||
        c.description?.toLowerCase().includes(search) ||
        c.prompt?.toLowerCase().includes(search)
    );
  }, [characters, characterSearch]);

  const filteredAnimations = useMemo(() => {
    if (!animationSearch.trim()) return animations;
    const search = animationSearch.toLowerCase();
    return animations.filter((a) => a.name.toLowerCase().includes(search));
  }, [animations, animationSearch]);

  // Load more handlers
  const handleLoadMoreCharacters = () => {
    const nextPage = characterPage + 1;
    setCharacterPage(nextPage);
    fetchCharacters(nextPage, true);
  };

  const handleLoadMoreAnimations = () => {
    const nextPage = animationPage + 1;
    setAnimationPage(nextPage);
    fetchAnimations(nextPage, true);
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Gallery</h1>
          <p className="text-muted-foreground mt-1">
            View all your characters and animations
          </p>
        </div>
        <Link href="/create">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            Create New
          </Button>
        </Link>
      </div>

      <Tabs defaultValue="characters" className="space-y-6">
        <TabsList>
          <TabsTrigger value="characters" className="gap-2">
            <Users className="h-4 w-4" />
            Characters
          </TabsTrigger>
          <TabsTrigger value="animations" className="gap-2">
            <Film className="h-4 w-4" />
            Animations
          </TabsTrigger>
        </TabsList>

        <TabsContent value="characters" className="space-y-4">
          {/* Filter Controls */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name or prompt..."
                value={characterSearch}
                onChange={(e) => setCharacterSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={characterStyle} onValueChange={setCharacterStyle}>
              <SelectTrigger className="w-full sm:w-[160px]">
                <SlidersHorizontal className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Style" />
              </SelectTrigger>
              <SelectContent>
                {STYLES.map((style) => (
                  <SelectItem key={style.value} value={style.value}>
                    {style.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={characterSort} onValueChange={setCharacterSort}>
              <SelectTrigger className="w-full sm:w-[160px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Characters Grid */}
          {isLoadingCharacters ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {[...Array(8)].map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-0">
                    <Skeleton className="aspect-square rounded-t-lg" />
                    <div className="p-4 space-y-2">
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-3 w-1/2" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : filteredCharacters.length === 0 ? (
            <Card>
              <CardHeader className="text-center py-12">
                <div className="flex justify-center mb-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                    <Users className="h-8 w-8 text-muted-foreground" />
                  </div>
                </div>
                <CardTitle>
                  {characters.length === 0 ? 'No characters yet' : 'No matching characters'}
                </CardTitle>
                <CardDescription>
                  {characters.length === 0
                    ? 'Create your first character to get started'
                    : 'Try adjusting your search or filters'}
                </CardDescription>
                {characters.length === 0 && (
                  <div className="pt-4">
                    <Link href="/characters/new">
                      <Button>
                        <Plus className="mr-2 h-4 w-4" />
                        Create Character
                      </Button>
                    </Link>
                  </div>
                )}
              </CardHeader>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {filteredCharacters.map((character) => (
                  <Link key={character.id} href={`/characters/${character.id}`}>
                    <Card className="overflow-hidden hover:border-primary/50 transition-colors">
                      <div className="aspect-square relative bg-muted">
                        {character.thumbnail_url ? (
                          <img
                            src={character.thumbnail_url}
                            alt={character.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Users className="h-12 w-12 text-muted-foreground" />
                          </div>
                        )}
                        {character.style && (
                          <span className="absolute top-2 right-2 text-xs bg-background/80 backdrop-blur-sm px-2 py-1 rounded-md capitalize">
                            {character.style}
                          </span>
                        )}
                      </div>
                      <CardContent className="p-4">
                        <h3 className="font-medium truncate">{character.name}</h3>
                        <p className="text-sm text-muted-foreground">
                          {new Date(character.created_at).toLocaleDateString()}
                        </p>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>

              {/* Load More Button */}
              {characterPage < characterTotalPages && !characterSearch && (
                <div className="flex justify-center pt-4">
                  <Button
                    variant="outline"
                    onClick={handleLoadMoreCharacters}
                    disabled={isLoadingMoreCharacters}
                  >
                    {isLoadingMoreCharacters ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      'Load More'
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>

        <TabsContent value="animations" className="space-y-4">
          {/* Filter Controls */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name..."
                value={animationSearch}
                onChange={(e) => setAnimationSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={animationType} onValueChange={setAnimationType}>
              <SelectTrigger className="w-full sm:w-[160px]">
                <SlidersHorizontal className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Type" />
              </SelectTrigger>
              <SelectContent>
                {ANIMATION_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={animationSort} onValueChange={setAnimationSort}>
              <SelectTrigger className="w-full sm:w-[160px]">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                {SORT_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Animations Grid */}
          {isLoadingAnimations ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {[...Array(8)].map((_, i) => (
                <Card key={i}>
                  <CardContent className="p-0">
                    <Skeleton className="aspect-video rounded-t-lg" />
                    <div className="p-4 space-y-2">
                      <Skeleton className="h-4 w-3/4" />
                      <Skeleton className="h-3 w-1/2" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : filteredAnimations.length === 0 ? (
            <Card>
              <CardHeader className="text-center py-12">
                <div className="flex justify-center mb-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted">
                    <Film className="h-8 w-8 text-muted-foreground" />
                  </div>
                </div>
                <CardTitle>
                  {animations.length === 0 ? 'No animations yet' : 'No matching animations'}
                </CardTitle>
                <CardDescription>
                  {animations.length === 0
                    ? 'Create your first animation to get started'
                    : 'Try adjusting your search or filters'}
                </CardDescription>
                {animations.length === 0 && (
                  <div className="pt-4">
                    <Link href="/animations/new">
                      <Button>
                        <Plus className="mr-2 h-4 w-4" />
                        Create Animation
                      </Button>
                    </Link>
                  </div>
                )}
              </CardHeader>
            </Card>
          ) : (
            <>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {filteredAnimations.map((animation) => (
                  <Link key={animation.id} href={`/animations/${animation.id}`}>
                    <Card className="overflow-hidden hover:border-primary/50 transition-colors">
                      <div className="aspect-video relative bg-muted">
                        {animation.thumbnail_url ? (
                          <img
                            src={animation.thumbnail_url}
                            alt={animation.name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Film className="h-12 w-12 text-muted-foreground" />
                          </div>
                        )}
                        {animation.type && (
                          <span className="absolute top-2 right-2 text-xs bg-background/80 backdrop-blur-sm px-2 py-1 rounded-md capitalize">
                            {animation.type}
                          </span>
                        )}
                      </div>
                      <CardContent className="p-4">
                        <h3 className="font-medium truncate">{animation.name}</h3>
                        <p className="text-sm text-muted-foreground">
                          {new Date(animation.created_at).toLocaleDateString()}
                        </p>
                      </CardContent>
                    </Card>
                  </Link>
                ))}
              </div>

              {/* Load More Button */}
              {animationPage < animationTotalPages && !animationSearch && (
                <div className="flex justify-center pt-4">
                  <Button
                    variant="outline"
                    onClick={handleLoadMoreAnimations}
                    disabled={isLoadingMoreAnimations}
                  >
                    {isLoadingMoreAnimations ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Loading...
                      </>
                    ) : (
                      'Load More'
                    )}
                  </Button>
                </div>
              )}
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
