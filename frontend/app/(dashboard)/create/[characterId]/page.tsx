'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { useAuth } from '@/contexts/auth-context';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ArrowLeft, Sparkles, CreditCard, Film, AlertCircle } from 'lucide-react';
import { GenerationProgress, AnimationStateSelector, type AnimationState } from '@/components/creator';
import type { Character, AnimationType } from '@/types';

const ANIMATION_STATES: (AnimationState & { id: AnimationType })[] = [
  { id: 'idle', label: 'Idle', description: 'Standing still animation', cost: 5 },
  { id: 'walk', label: 'Walk', description: 'Walking cycle animation', cost: 5 },
  { id: 'run', label: 'Run', description: 'Running cycle animation', cost: 5 },
  { id: 'jump', label: 'Jump', description: 'Jumping animation', cost: 5 },
  { id: 'attack', label: 'Attack', description: 'Attack/combat animation', cost: 5 },
];

const CREDIT_COST_PER_ANIMATION = 5;

export default function AnimationGeneratorPage() {
  const params = useParams();
  const router = useRouter();
  const characterId = params.characterId as string;
  const { credits, refreshCredits } = useAuth();

  const [character, setCharacter] = useState<Character | null>(null);
  const [isLoadingCharacter, setIsLoadingCharacter] = useState(true);
  const [selectedStates, setSelectedStates] = useState<AnimationType[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationIds, setGenerationIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const totalCost = selectedStates.length * CREDIT_COST_PER_ANIMATION;
  const hasEnoughCredits = (credits?.credits ?? 0) >= totalCost;

  useEffect(() => {
    const fetchCharacter = async () => {
      try {
        const data = await api.getCharacter(characterId);
        setCharacter(data);
      } catch (err) {
        setError('Failed to load character');
        console.error('Failed to fetch character:', err);
      } finally {
        setIsLoadingCharacter(false);
      }
    };
    fetchCharacter();
  }, [characterId]);

  const handleStateToggle = (stateId: string) => {
    const animationType = stateId as AnimationType;
    setSelectedStates((prev) =>
      prev.includes(animationType)
        ? prev.filter((id) => id !== animationType)
        : [...prev, animationType]
    );
  };

  const handleSelectAll = () => {
    if (selectedStates.length === ANIMATION_STATES.length) {
      setSelectedStates([]);
    } else {
      setSelectedStates(ANIMATION_STATES.map((s) => s.id));
    }
  };

  const handleGenerate = async () => {
    if (selectedStates.length === 0) {
      setError('Please select at least one animation state');
      return;
    }

    if (!hasEnoughCredits) {
      setError('Not enough credits. Please purchase more credits to continue.');
      return;
    }

    setIsGenerating(true);
    setError(null);

    try {
      const generationPromises = selectedStates.map((stateType) =>
        api.createAnimation({
          character_id: characterId,
          type: stateType,
          name: `${character?.name} - ${stateType}`,
        })
      );

      const generations = await Promise.all(generationPromises);
      setGenerationIds(generations.map((g) => g.id));
      await refreshCredits();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start generation');
      setIsGenerating(false);
    }
  };

  const handleGenerationComplete = () => {
    router.push(`/animations?character=${characterId}`);
  };

  if (isLoadingCharacter) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-32" />
          </div>
        </div>
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!character) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">Character not found</h3>
            <p className="text-muted-foreground text-center mb-4">
              The character you're looking for doesn't exist or has been deleted
            </p>
            <Link href="/characters">
              <Button>Back to Characters</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (generationIds.length > 0) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <Film className="h-6 w-6 text-primary" />
          </div>
          <div>
            <h1 className="text-3xl font-bold">Generating Animations</h1>
            <p className="text-muted-foreground">
              Creating {generationIds.length} animation{generationIds.length > 1 ? 's' : ''} for {character.name}
            </p>
          </div>
        </div>

        <div className="space-y-4">
          {generationIds.map((id, index) => (
            <GenerationProgress
              key={id}
              jobId={id}
              title={`${selectedStates[index] || 'Animation'}`}
              onComplete={index === generationIds.length - 1 ? handleGenerationComplete : undefined}
            />
          ))}
        </div>

        <div className="text-center">
          <p className="text-sm text-muted-foreground mb-4">
            You'll be redirected to your animations once generation is complete
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link href={`/characters`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Generate Animations</h1>
          <p className="text-muted-foreground">Select animation states for your character</p>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Animation States</CardTitle>
                <CardDescription>
                  Select the animations you want to generate
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              {error && (
                <div className="p-3 mb-4 text-sm text-destructive bg-destructive/10 rounded-md">
                  {error}
                </div>
              )}

              <AnimationStateSelector
                states={ANIMATION_STATES}
                selectedStates={selectedStates}
                onToggle={handleStateToggle}
                onSelectAll={handleSelectAll}
                disabled={isGenerating}
                showCost
              />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-medium">Total Cost</p>
                  <p className="text-2xl font-bold">{totalCost} credits</p>
                </div>
                <Badge
                  variant={hasEnoughCredits && totalCost > 0 ? 'secondary' : 'destructive'}
                  className="text-sm"
                >
                  <CreditCard className="h-3 w-3 mr-1" />
                  Balance: {credits?.credits ?? 0}
                </Badge>
              </div>

              <Button
                className="w-full"
                size="lg"
                onClick={handleGenerate}
                disabled={isGenerating || selectedStates.length === 0 || !hasEnoughCredits}
              >
                {isGenerating ? (
                  'Starting generation...'
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate {selectedStates.length} Animation{selectedStates.length !== 1 ? 's' : ''}
                  </>
                )}
              </Button>

              {!hasEnoughCredits && selectedStates.length > 0 && (
                <div className="text-center mt-4">
                  <p className="text-sm text-muted-foreground mb-2">
                    You need {totalCost - (credits?.credits ?? 0)} more credits
                  </p>
                  <Link href="/billing">
                    <Button variant="outline" size="sm">
                      Buy Credits
                    </Button>
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium">Character</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="aspect-square relative rounded-lg overflow-hidden bg-muted mb-3">
                {character.thumbnail_url || character.image_url ? (
                  <img
                    src={character.thumbnail_url || character.image_url}
                    alt={character.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <span className="text-muted-foreground">No image</span>
                  </div>
                )}
              </div>
              <h3 className="font-semibold">{character.name}</h3>
              {character.description && (
                <p className="text-sm text-muted-foreground mt-1">
                  {character.description}
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
