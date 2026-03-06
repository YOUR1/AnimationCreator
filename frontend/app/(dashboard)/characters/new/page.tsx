'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import api from '@/lib/api';
import { useAuth } from '@/contexts/auth-context';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { ArrowLeft, Sparkles, CreditCard } from 'lucide-react';
import Link from 'next/link';
import { StyleSelector, CharacterPromptInput, type StyleOption } from '@/components/creator';

const characterStyles: StyleOption[] = [
  { value: 'anime', label: 'Anime', description: 'Japanese animation style' },
  { value: 'cartoon', label: 'Cartoon', description: '2D cartoon style' },
  { value: 'realistic', label: 'Realistic', description: 'Photo-realistic style' },
  { value: 'pixel', label: 'Pixel Art', description: 'Retro pixel art style' },
  { value: '3d', label: '3D Render', description: '3D rendered style' },
];

const CHARACTER_COST = 10; // Credits per character

export default function NewCharacterPage() {
  const router = useRouter();
  const { credits, refreshCredits } = useAuth();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [style, setStyle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasEnoughCredits = (credits?.credits ?? 0) >= CHARACTER_COST;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!hasEnoughCredits) {
      setError('Not enough credits. Please purchase more credits to continue.');
      return;
    }

    setIsGenerating(true);

    try {
      const generation = await api.createCharacter({
        name,
        description: description || undefined,
        style,
        prompt,
      });

      // Refresh credits after generation starts
      await refreshCredits();

      // Redirect to generation status page or character page
      router.push(`/characters?generation=${generation.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create character');
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/characters">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold">Create Character</h1>
          <p className="text-muted-foreground">Generate a new character with AI</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Character Details</CardTitle>
              <CardDescription>Describe your character for AI generation</CardDescription>
            </div>
            <Badge variant={hasEnoughCredits ? 'secondary' : 'destructive'}>
              <CreditCard className="h-3 w-3 mr-1" />
              {CHARACTER_COST} credits
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
              <Label htmlFor="name">Character Name</Label>
              <Input
                id="name"
                placeholder="e.g., Luna the Explorer"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                disabled={isGenerating}
              />
            </div>

            <div className="space-y-2">
              <Label>Art Style</Label>
              <StyleSelector
                styles={characterStyles}
                selectedStyle={style}
                onSelect={setStyle}
                disabled={isGenerating}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="prompt">Character Description</Label>
              <CharacterPromptInput
                value={prompt}
                onChange={setPrompt}
                maxLength={1000}
                placeholder="Describe your character in detail... e.g., A young female explorer with bright blue eyes, wearing a safari hat and brown leather jacket. She has curly red hair and a friendly smile."
                disabled={isGenerating}
                rows={4}
                hint="Be specific about appearance, clothing, and distinctive features"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Notes (optional)</Label>
              <Input
                id="description"
                placeholder="Personal notes about this character"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                disabled={isGenerating}
              />
            </div>

            <div className="flex gap-4">
              <Button
                type="submit"
                className="flex-1"
                disabled={isGenerating || !hasEnoughCredits}
              >
                {isGenerating ? (
                  <>Generating...</>
                ) : (
                  <>
                    <Sparkles className="h-4 w-4 mr-2" />
                    Generate Character
                  </>
                )}
              </Button>
            </div>

            {!hasEnoughCredits && (
              <div className="text-center">
                <p className="text-sm text-muted-foreground mb-2">
                  You need {CHARACTER_COST} credits to generate a character
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
    </div>
  );
}
