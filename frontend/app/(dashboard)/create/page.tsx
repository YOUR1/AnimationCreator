'use client';

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Users, Film, Wand2 } from 'lucide-react';
import Link from 'next/link';

export default function CreatePage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Create</h1>
        <p className="text-muted-foreground mt-1">
          Choose what you'd like to create
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        <Card className="hover:border-primary/50 transition-colors cursor-pointer">
          <Link href="/characters/new">
            <CardHeader>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 mb-4">
                <Users className="h-6 w-6 text-primary" />
              </div>
              <CardTitle>New Character</CardTitle>
              <CardDescription>
                Create a new character to animate using AI
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full">
                <Wand2 className="mr-2 h-4 w-4" />
                Create Character
              </Button>
            </CardContent>
          </Link>
        </Card>

        <Card className="hover:border-primary/50 transition-colors cursor-pointer">
          <Link href="/animations/new">
            <CardHeader>
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 mb-4">
                <Film className="h-6 w-6 text-primary" />
              </div>
              <CardTitle>New Animation</CardTitle>
              <CardDescription>
                Generate animations from your existing characters
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full" variant="outline">
                <Wand2 className="mr-2 h-4 w-4" />
                Create Animation
              </Button>
            </CardContent>
          </Link>
        </Card>
      </div>
    </div>
  );
}
