'use client';

import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export interface AnimationState {
  id: string;
  label: string;
  description: string;
  cost?: number;
}

interface AnimationStateSelectorProps {
  states: AnimationState[];
  selectedStates: string[];
  onToggle: (stateId: string) => void;
  onSelectAll?: () => void;
  disabled?: boolean;
  showCost?: boolean;
  className?: string;
}

export function AnimationStateSelector({
  states,
  selectedStates,
  onToggle,
  onSelectAll,
  disabled = false,
  showCost = false,
  className,
}: AnimationStateSelectorProps) {
  const allSelected = selectedStates.length === states.length;

  return (
    <div className={cn('space-y-3', className)}>
      {onSelectAll && (
        <div className="flex justify-end mb-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onSelectAll}
            disabled={disabled}
          >
            {allSelected ? 'Deselect All' : 'Select All'}
          </Button>
        </div>
      )}

      {states.map((state) => {
        const isSelected = selectedStates.includes(state.id);

        return (
          <div
            key={state.id}
            className={cn(
              'flex items-center space-x-3 p-3 rounded-lg border cursor-pointer transition-colors',
              isSelected
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-primary/50',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
            onClick={() => !disabled && onToggle(state.id)}
          >
            <Checkbox
              id={state.id}
              checked={isSelected}
              onCheckedChange={() => onToggle(state.id)}
              disabled={disabled}
            />
            <div className="flex-1">
              <Label
                htmlFor={state.id}
                className="text-sm font-medium cursor-pointer"
              >
                {state.label}
              </Label>
              <p className="text-xs text-muted-foreground">
                {state.description}
              </p>
            </div>
            {showCost && state.cost !== undefined && (
              <Badge variant="secondary" className="text-xs">
                {state.cost} credits
              </Badge>
            )}
          </div>
        );
      })}
    </div>
  );
}
