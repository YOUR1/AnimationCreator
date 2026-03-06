"use client";

import { Coins } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface CreditBadgeProps {
  credits: number;
  isLoading?: boolean;
  showIcon?: boolean;
  className?: string;
  variant?: "default" | "secondary" | "outline";
}

export function CreditBadge({
  credits,
  isLoading = false,
  showIcon = true,
  className,
  variant = "secondary",
}: CreditBadgeProps) {
  if (isLoading) {
    return <Skeleton className="h-6 w-20" />;
  }

  return (
    <Badge variant={variant} className={cn("gap-1", className)}>
      {showIcon && <Coins className="h-3 w-3" />}
      <span>{credits.toLocaleString()} credits</span>
    </Badge>
  );
}

export function CreditDisplay({
  credits,
  isLoading = false,
  className,
}: {
  credits: number;
  isLoading?: boolean;
  className?: string;
}) {
  if (isLoading) {
    return <Skeleton className="h-8 w-24" />;
  }

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Coins className="h-5 w-5 text-yellow-500" />
      <span className="text-lg font-semibold">{credits.toLocaleString()}</span>
      <span className="text-sm text-muted-foreground">credits</span>
    </div>
  );
}
