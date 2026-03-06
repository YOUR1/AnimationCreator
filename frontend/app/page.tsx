import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Film, Sparkles, Zap, Users, Download, CreditCard } from 'lucide-react';

const features = [
  {
    icon: Sparkles,
    title: 'AI-Powered Generation',
    description: 'Create stunning characters and animations with state-of-the-art AI models',
  },
  {
    icon: Users,
    title: 'Character Library',
    description: 'Build your own library of unique characters in various art styles',
  },
  {
    icon: Film,
    title: 'Smooth Animations',
    description: 'Generate fluid animations with customizable duration and frame rates',
  },
  {
    icon: Download,
    title: 'Multiple Formats',
    description: 'Export your animations as MP4, GIF, or WebM for any platform',
  },
  {
    icon: Zap,
    title: 'Fast Processing',
    description: 'Get your animations rendered quickly with our optimized pipeline',
  },
  {
    icon: CreditCard,
    title: 'Pay As You Go',
    description: 'Only pay for what you use with our flexible credit system',
  },
];

const pricingTiers = [
  { credits: 100, price: 9.99, perCredit: 0.0999 },
  { credits: 500, price: 39.99, perCredit: 0.08, popular: true },
  { credits: 1000, price: 69.99, perCredit: 0.07 },
];

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      {/* Header */}
      <header className="container mx-auto px-4 py-6">
        <nav className="flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Film className="h-8 w-8 text-primary" />
            <span className="text-xl font-bold">AnimationCreator</span>
          </Link>
          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost">Sign in</Button>
            </Link>
            <Link href="/register">
              <Button>Get Started</Button>
            </Link>
          </div>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-24 text-center">
        <Badge className="mb-4" variant="secondary">
          Powered by AI
        </Badge>
        <h1 className="text-5xl md:text-6xl font-bold tracking-tight mb-6">
          Create Stunning
          <br />
          <span className="text-primary">Character Animations</span>
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
          Generate unique characters and bring them to life with AI-powered animation.
          No design skills required.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/register">
            <Button size="lg" className="gap-2">
              <Sparkles className="h-5 w-5" />
              Start Creating
            </Button>
          </Link>
          <Link href="#features">
            <Button size="lg" variant="outline">
              Learn More
            </Button>
          </Link>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="container mx-auto px-4 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Everything You Need</h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            From character creation to animation export, we've got you covered
          </p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature) => (
            <Card key={feature.title}>
              <CardHeader>
                <feature.icon className="h-10 w-10 text-primary mb-2" />
                <CardTitle>{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="container mx-auto px-4 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Simple Pricing</h2>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Buy credits and use them whenever you want. No subscriptions required.
          </p>
        </div>
        <div className="grid md:grid-cols-3 gap-6 max-w-4xl mx-auto">
          {pricingTiers.map((tier) => (
            <Card
              key={tier.credits}
              className={tier.popular ? 'border-primary shadow-lg scale-105' : ''}
            >
              {tier.popular && (
                <div className="bg-primary text-primary-foreground text-center py-1 text-sm font-medium">
                  Most Popular
                </div>
              )}
              <CardHeader className="text-center">
                <CardTitle className="text-2xl">{tier.credits} Credits</CardTitle>
                <div className="mt-4">
                  <span className="text-4xl font-bold">${tier.price}</span>
                </div>
                <CardDescription>
                  ${tier.perCredit.toFixed(3)} per credit
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Link href="/register">
                  <Button className="w-full" variant={tier.popular ? 'default' : 'outline'}>
                    Get Started
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
        <p className="text-center text-sm text-muted-foreground mt-8">
          Character generation: ~10 credits | Animation: ~25 credits
        </p>
      </section>

      {/* CTA Section */}
      <section className="container mx-auto px-4 py-24">
        <Card className="bg-primary text-primary-foreground">
          <CardContent className="py-16 text-center">
            <h2 className="text-3xl font-bold mb-4">Ready to Start Creating?</h2>
            <p className="mb-8 text-primary-foreground/80 max-w-xl mx-auto">
              Join thousands of creators using AnimationCreator to bring their characters to life.
            </p>
            <Link href="/register">
              <Button size="lg" variant="secondary" className="gap-2">
                <Sparkles className="h-5 w-5" />
                Create Your First Animation
              </Button>
            </Link>
          </CardContent>
        </Card>
      </section>

      {/* Footer */}
      <footer className="border-t">
        <div className="container mx-auto px-4 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Film className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                AnimationCreator
              </span>
            </div>
            <div className="flex gap-6 text-sm text-muted-foreground">
              <Link href="/terms" className="hover:text-foreground">
                Terms
              </Link>
              <Link href="/privacy" className="hover:text-foreground">
                Privacy
              </Link>
              <Link href="/contact" className="hover:text-foreground">
                Contact
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
