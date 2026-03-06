'use client';

import { useState, useEffect } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import api from '@/lib/api';
import { useAuth } from '@/contexts/auth-context';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { CreditDisplay } from '@/components/shared/CreditBadge';
import { CreditCard, History, Sparkles } from 'lucide-react';
import type { CreditPack, Transaction } from '@/types';

export default function BillingPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { credits, refreshCredits } = useAuth();
  const { toast } = useToast();
  const [packs, setPacks] = useState<CreditPack[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isLoadingPacks, setIsLoadingPacks] = useState(true);
  const [isLoadingTransactions, setIsLoadingTransactions] = useState(true);
  const [purchaseLoading, setPurchaseLoading] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [packsData, transactionsData] = await Promise.all([
          api.getCreditPacks(),
          api.getTransactionHistory(1, 10),
        ]);
        setPacks(packsData);
        setTransactions(transactionsData.items);
      } catch (error) {
        console.error('Failed to fetch billing data:', error);
      } finally {
        setIsLoadingPacks(false);
        setIsLoadingTransactions(false);
      }
    };
    fetchData();
  }, []);

  // Handle Stripe checkout redirects
  useEffect(() => {
    const success = searchParams.get('success');
    const cancelled = searchParams.get('cancelled');

    if (success === 'true') {
      toast({
        title: 'Purchase successful',
        description: 'Your credits have been added to your account.',
      });
      refreshCredits();
      // Clear URL params
      router.replace('/billing', { scroll: false });
    } else if (cancelled === 'true') {
      toast({
        title: 'Purchase cancelled',
        description: 'Your checkout session was cancelled.',
        variant: 'destructive',
      });
      // Clear URL params
      router.replace('/billing', { scroll: false });
    }
  }, [searchParams, toast, refreshCredits, router]);

  const handlePurchase = async (packId: string) => {
    setPurchaseLoading(packId);
    try {
      const session = await api.createCheckoutSession(packId);
      window.location.href = session.url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
    } finally {
      setPurchaseLoading(null);
    }
  };

  const handleManageBilling = async () => {
    try {
      const { url } = await api.getBillingPortalUrl();
      window.location.href = url;
    } catch (error) {
      console.error('Failed to get billing portal URL:', error);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Billing</h1>
        <p className="text-muted-foreground mt-1">
          Manage your credits and billing
        </p>
      </div>

      {/* Current Balance */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
            Current Balance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <CreditDisplay credits={credits?.credits ?? 0} />
        </CardContent>
        <CardFooter>
          <Button variant="outline" onClick={handleManageBilling}>
            Manage Billing
          </Button>
        </CardFooter>
      </Card>

      {/* Credit Packs */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Buy Credits</h2>
        {isLoadingPacks ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(3)].map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-6 w-24" />
                  <Skeleton className="h-4 w-32" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-10 w-20" />
                </CardContent>
                <CardFooter>
                  <Skeleton className="h-10 w-full" />
                </CardFooter>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {packs.map((pack) => (
              <Card key={pack.id} className={pack.popular ? 'border-primary' : ''}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{pack.name}</CardTitle>
                    {pack.popular && (
                      <Badge className="gap-1">
                        <Sparkles className="h-3 w-3" />
                        Popular
                      </Badge>
                    )}
                  </div>
                  <CardDescription>
                    {pack.credits.toLocaleString()} credits
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    ${(pack.price / 100).toFixed(2)}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    ${((pack.price / 100) / pack.credits).toFixed(3)} per credit
                  </p>
                </CardContent>
                <CardFooter>
                  <Button
                    className="w-full"
                    variant={pack.popular ? 'default' : 'outline'}
                    onClick={() => handlePurchase(pack.id)}
                    disabled={purchaseLoading === pack.id}
                  >
                    {purchaseLoading === pack.id ? 'Processing...' : 'Buy Now'}
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Transaction History */}
      <div>
        <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
          <History className="h-5 w-5" />
          Recent Transactions
        </h2>
        {isLoadingTransactions ? (
          <Card>
            <CardContent className="py-6 space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center justify-between">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                  <Skeleton className="h-4 w-16" />
                </div>
              ))}
            </CardContent>
          </Card>
        ) : transactions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">No transactions yet</p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="py-2">
              <div className="divide-y">
                {transactions.map((transaction) => (
                  <div key={transaction.id} className="py-4 flex items-center justify-between">
                    <div>
                      <p className="font-medium">{transaction.description}</p>
                      <p className="text-sm text-muted-foreground">
                        {new Date(transaction.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className={`font-medium ${transaction.amount > 0 ? 'text-green-600' : 'text-muted-foreground'}`}>
                      {transaction.amount > 0 ? '+' : ''}{transaction.amount} credits
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
