'use client';

import { Badge } from '@/components/ui/badge';
import { Clock, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { GenerationStatus } from '@/types';

interface JobStatusBadgeProps {
  status: GenerationStatus;
  className?: string;
  showIcon?: boolean;
}

const statusConfig: Record<
  GenerationStatus,
  {
    label: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline';
    icon: React.ElementType;
    iconClass?: string;
  }
> = {
  pending: {
    label: 'Pending',
    variant: 'outline',
    icon: Clock,
    iconClass: 'text-muted-foreground',
  },
  processing: {
    label: 'Processing',
    variant: 'default',
    icon: Loader2,
    iconClass: 'animate-spin',
  },
  completed: {
    label: 'Completed',
    variant: 'secondary',
    icon: CheckCircle,
    iconClass: 'text-green-500',
  },
  failed: {
    label: 'Failed',
    variant: 'destructive',
    icon: XCircle,
  },
};

export function JobStatusBadge({
  status,
  className,
  showIcon = true,
}: JobStatusBadgeProps) {
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <Badge variant={config.variant} className={cn('', className)}>
      {showIcon && (
        <Icon className={cn('h-3 w-3 mr-1', config.iconClass)} />
      )}
      {config.label}
    </Badge>
  );
}
