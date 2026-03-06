'use client';

import { Button } from '@/components/ui/button';
import { Check, RefreshCw, X, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ApprovalButtonsProps {
  onApprove: () => void;
  onRegenerate: () => void;
  onReject?: () => void;
  isApproving?: boolean;
  isRegenerating?: boolean;
  disabled?: boolean;
  showReject?: boolean;
  className?: string;
}

export function ApprovalButtons({
  onApprove,
  onRegenerate,
  onReject,
  isApproving = false,
  isRegenerating = false,
  disabled = false,
  showReject = false,
  className,
}: ApprovalButtonsProps) {
  const isLoading = isApproving || isRegenerating;

  return (
    <div className={cn('flex gap-3', className)}>
      <Button
        onClick={onApprove}
        disabled={disabled || isLoading}
        className="flex-1"
      >
        {isApproving ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Approving...
          </>
        ) : (
          <>
            <Check className="h-4 w-4 mr-2" />
            Approve
          </>
        )}
      </Button>
      <Button
        variant="outline"
        onClick={onRegenerate}
        disabled={disabled || isLoading}
        className="flex-1"
      >
        {isRegenerating ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Regenerating...
          </>
        ) : (
          <>
            <RefreshCw className="h-4 w-4 mr-2" />
            Regenerate
          </>
        )}
      </Button>
      {showReject && onReject && (
        <Button
          variant="destructive"
          onClick={onReject}
          disabled={disabled || isLoading}
          size="icon"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
