'use client';

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import api from '@/lib/api';
import { useAuth } from '@/contexts/auth-context';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ArrowLeft, Sparkles, CreditCard, Users, ChevronDown, Settings2 } from 'lucide-react';
import type { Character, AnimationType, AspectRatio, SpecialFx } from '@/types';

const ANIMATION_COST = 25; // Credits per animation

const ANIMATION_TYPES: { value: AnimationType; label: string; description: string }[] = [
  { value: 'idle', label: 'Idle', description: 'Subtle breathing and idle movement' },
  { value: 'walk', label: 'Walk', description: 'Walking cycle animation' },
  { value: 'run', label: 'Run', description: 'Running cycle animation' },
  { value: 'jump', label: 'Jump', description: 'Jumping motion' },
  { value: 'attack', label: 'Attack', description: 'Combat/attack motion' },
  { value: 'dancing', label: 'Dancing', description: 'Happy dancing movement' },
  { value: 'sad', label: 'Sad', description: 'Sad, disappointed expression' },
  { value: 'excited', label: 'Excited', description: 'Bouncing with excitement' },
  { value: 'custom', label: 'Custom', description: 'Describe your own animation' },
];

const SPECIAL_FX_OPTIONS: { value: SpecialFx; label: string }[] = [
  { value: 'hug', label: 'Hug' },
  { value: 'kiss', label: 'Kiss' },
  { value: 'heart_gesture', label: 'Heart Gesture' },
  { value: 'squish', label: 'Squish' },
  { value: 'expansion', label: 'Expansion' },
];

export default function NewAnimationPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedCharacterId = searchParams.get('character');
  const { credits, refreshCredits } = useAuth();

  const [characters, setCharacters] = useState<Character[]>([]);
  const [isLoadingCharacters, setIsLoadingCharacters] = useState(true);
  const [characterId, setCharacterId] = useState(preselectedCharacterId || '');
  const [name, setName] = useState('');
  const [animationType, setAnimationType] = useState<AnimationType>('idle');
  const [prompt, setPrompt] = useState('');
  const [duration, setDuration] = useState<5 | 10>(5);
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('1:1');
  const [negativePrompt, setNegativePrompt] = useState('');
  const [cfgScale, setCfgScale] = useState([0.5]);
  const [specialFx, setSpecialFx] = useState<SpecialFx | 'none'>('none');
  const [seamlessLoop, setSeamlessLoop] = useState(false);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasEnoughCredits = (credits?.credits ?? 0) >= ANIMATION_COST;

  useEffect(() => {
    const fetchCharacters = async () => {
      try {
        const response = await api.getCharacters(1, 100);
        setCharacters(response.items.filter((c) => c.status === 'completed'));
      } catch (error) {
        console.error('Failed to fetch characters:', error);
      } finally {
        setIsLoadingCharacters(false);
      }
    };
    fetchCharacters();
  }, []);

  const selectedCharacter = characters.find((c) => c.id === characterId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!hasEnoughCredits) {
      setError('Not enough credits. Please purchase more credits to continue.');
      return;
    }

    if (!characterId) {
      setError('Please select a character');
      return;
    }

    setIsGenerating(true);

    try {
      const response = await api.createAnimation({
        character_id: characterId,
        type: animationType,
        name,
        prompt: prompt || undefined,
        duration,
        aspect_ratio: aspectRatio,
        negative_prompt: negativePrompt || undefined,
        cfg_scale: cfgScale[0],
        special_fx: specialFx !== 'none' ? specialFx : undefined,
        seamless_loop: seamlessLoop,
      });

      await refreshCredits();
      router.push(`/animations?job=${response.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create animation');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/animations">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Create Animation</h1>
          <p className="text-muted-foreground">Animate your character with AI</p>
        </div>
      </div>

      {isLoadingCharacters ? (
        <Card>
          <CardContent className="py-8">
            <div className="flex justify-center">
              <Skeleton className="h-32 w-full max-w-md" />
            </div>
          </CardContent>
        </Card>
      ) : characters.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-16">
            <Users className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No characters available</h3>
            <p className="text-muted-foreground text-center mb-4">
              You need to create a character first before making animations
            </p>
            <Link href="/characters/new">
              <Button>Create Character</Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Animation Details</CardTitle>
                <CardDescription>Configure your animation settings</CardDescription>
              </div>
              <Badge variant={hasEnoughCredits ? 'secondary' : 'destructive'}>
                <CreditCard className="h-3 w-3 mr-1" />
                {ANIMATION_COST} credits
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {error && (
                <div className="p-3 text-sm text-destructive bg-destructive/10 rounded-md">
                  {error}
                </div>
              )}

              <div className="space-y-2">
                <Label htmlFor="character">Character</Label>
                <Select value={characterId} onValueChange={setCharacterId} required disabled={isGenerating}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a character" />
                  </SelectTrigger>
                  <SelectContent>
                    {characters.map((character) => (
                      <SelectItem key={character.id} value={character.id}>
                        <div className="flex items-center gap-2">
                          {character.thumbnail_url && (
                            <img
                              src={character.thumbnail_url}
                              alt={character.name}
                              className="w-6 h-6 rounded object-cover"
                            />
                          )}
                          {character.name}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {selectedCharacter && (
                  <div className="flex items-center gap-3 p-3 bg-muted rounded-lg">
                    {selectedCharacter.thumbnail_url && (
                      <img
                        src={selectedCharacter.thumbnail_url}
                        alt={selectedCharacter.name}
                        className="w-16 h-16 rounded object-cover"
                      />
                    )}
                    <div>
                      <p className="font-medium">{selectedCharacter.name}</p>
                      <p className="text-sm text-muted-foreground">{selectedCharacter.style}</p>
                    </div>
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="type">Animation Type</Label>
                <Select value={animationType} onValueChange={(v) => setAnimationType(v as AnimationType)} disabled={isGenerating}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select animation type" />
                  </SelectTrigger>
                  <SelectContent>
                    {ANIMATION_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        <div className="flex flex-col">
                          <span>{type.label}</span>
                          <span className="text-xs text-muted-foreground">{type.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Animation Name</Label>
                <Input
                  id="name"
                  placeholder="e.g., Walking cycle"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  disabled={isGenerating}
                />
              </div>

              {animationType === 'custom' && (
                <div className="space-y-2">
                  <Label htmlFor="prompt">Animation Description</Label>
                  <Textarea
                    id="prompt"
                    placeholder="Describe the animation... e.g., Character walking forward with a confident stride, arms swinging naturally"
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    required
                    disabled={isGenerating}
                    rows={3}
                  />
                </div>
              )}

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Duration</Label>
                    <Select
                      value={duration.toString()}
                      onValueChange={(v) => setDuration(parseInt(v) as 5 | 10)}
                      disabled={isGenerating}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="5">5 seconds</SelectItem>
                        <SelectItem value="10">10 seconds</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Aspect Ratio</Label>
                    <Select
                      value={aspectRatio}
                      onValueChange={(v) => setAspectRatio(v as AspectRatio)}
                      disabled={isGenerating}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1:1">1:1 (Square)</SelectItem>
                        <SelectItem value="16:9">16:9 (Landscape)</SelectItem>
                        <SelectItem value="9:16">9:16 (Portrait)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Advanced Settings */}
              <Collapsible open={showAdvanced}>
                <CollapsibleTrigger asChild>
                  <Button
                    variant="ghost"
                    className="w-full justify-between"
                    type="button"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                  >
                    <span className="flex items-center gap-2">
                      <Settings2 className="h-4 w-4" />
                      Advanced Settings
                    </span>
                    <ChevronDown className={`h-4 w-4 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
                  </Button>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-4 pt-4">
                  <div className="space-y-2">
                    <Label htmlFor="negative_prompt">Negative Prompt</Label>
                    <Textarea
                      id="negative_prompt"
                      placeholder="Elements to avoid... e.g., shadows, blur, multiple characters"
                      value={negativePrompt}
                      onChange={(e) => setNegativePrompt(e.target.value)}
                      disabled={isGenerating}
                      rows={2}
                    />
                    <p className="text-xs text-muted-foreground">
                      By default, shadows and other unwanted elements are already filtered out.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>CFG Scale</Label>
                      <span className="text-sm text-muted-foreground">{cfgScale[0].toFixed(2)}</span>
                    </div>
                    <Slider
                      value={cfgScale}
                      onValueChange={setCfgScale}
                      min={0}
                      max={1}
                      step={0.05}
                      disabled={isGenerating}
                    />
                    <p className="text-xs text-muted-foreground">
                      Higher values follow the prompt more strictly.
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Special Effects</Label>
                    <Select
                      value={specialFx}
                      onValueChange={(v) => setSpecialFx(v as SpecialFx | 'none')}
                      disabled={isGenerating}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="None" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">None</SelectItem>
                        {SPECIAL_FX_OPTIONS.map((fx) => (
                          <SelectItem key={fx.value} value={fx.value}>
                            {fx.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <Label htmlFor="seamless-loop">Seamless Loop</Label>
                      <p className="text-xs text-muted-foreground">
                        Creates a smooth ping-pong loop. Recommended when creating multiple
                        animations (idle, walk, run) for seamless transitions between states.
                      </p>
                    </div>
                    <Switch
                      id="seamless-loop"
                      checked={seamlessLoop}
                      onCheckedChange={setSeamlessLoop}
                      disabled={isGenerating}
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>

              <Button
                type="submit"
                className="w-full"
                disabled={isGenerating || !hasEnoughCredits || !characterId}
              >
                {isGenerating ? (
                  <>Generating...</>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Animation
                  </>
                )}
              </Button>

              {!hasEnoughCredits && (
                <div className="text-center">
                  <p className="text-sm text-muted-foreground mb-2">
                    You need {ANIMATION_COST} credits to generate an animation
                  </p>
                  <Link href="/billing">
                    <Button variant="outline" size="sm">
                      Buy Credits
                    </Button>
                  </Link>
                </div>
              )}
            </form>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
