'use client';

import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { Check } from 'lucide-react';

export interface StyleOption {
  value: string;
  label: string;
  description: string;
  icon?: React.ReactNode;
}

interface StyleSelectorProps {
  styles: StyleOption[];
  selectedStyle: string;
  onSelect: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

export function StyleSelector({
  styles,
  selectedStyle,
  onSelect,
  disabled = false,
  className,
}: StyleSelectorProps) {
  return (
    <div className={cn('grid grid-cols-2 sm:grid-cols-3 gap-3', className)}>
      {styles.map((style) => {
        const isSelected = selectedStyle === style.value;

        return (
          <Card
            key={style.value}
            className={cn(
              'cursor-pointer transition-all duration-200 hover:shadow-md',
              isSelected
                ? 'ring-2 ring-primary border-primary bg-primary/5'
                : 'hover:border-primary/50',
              disabled && 'opacity-50 cursor-not-allowed'
            )}
            onClick={() => !disabled && onSelect(style.value)}
          >
            <CardContent className="p-4 relative">
              {isSelected && (
                <div className="absolute top-2 right-2">
                  <div className="h-5 w-5 rounded-full bg-primary flex items-center justify-center">
                    <Check className="h-3 w-3 text-primary-foreground" />
                  </div>
                </div>
              )}
              <div className="space-y-2">
                {style.icon && (
                  <div className="text-muted-foreground">{style.icon}</div>
                )}
                <div>
                  <h4 className="font-medium text-sm">{style.label}</h4>
                  <p className="text-xs text-muted-foreground mt-1">
                    {style.description}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
