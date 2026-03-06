'use client';

import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

interface CharacterPromptInputProps {
  value: string;
  onChange: (value: string) => void;
  maxLength?: number;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
  hint?: string;
  className?: string;
}

export function CharacterPromptInput({
  value,
  onChange,
  maxLength,
  placeholder = 'Describe your character in detail...',
  disabled = false,
  rows = 4,
  hint,
  className,
}: CharacterPromptInputProps) {
  const characterCount = value.length;
  const isNearLimit = maxLength && characterCount >= maxLength * 0.9;
  const isAtLimit = maxLength && characterCount >= maxLength;

  return (
    <div className={cn('space-y-2', className)}>
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        rows={rows}
        maxLength={maxLength}
        className={cn(
          isAtLimit && 'border-destructive focus-visible:ring-destructive'
        )}
      />
      <div className="flex items-center justify-between">
        {hint && (
          <p className="text-xs text-muted-foreground">{hint}</p>
        )}
        {maxLength && (
          <p
            className={cn(
              'text-xs text-muted-foreground ml-auto',
              isNearLimit && !isAtLimit && 'text-yellow-600',
              isAtLimit && 'text-destructive'
            )}
          >
            {characterCount}/{maxLength}
          </p>
        )}
      </div>
    </div>
  );
}
