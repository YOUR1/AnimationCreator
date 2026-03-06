'use client';

import * as React from 'react';

interface CollapsibleProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  children: React.ReactNode;
}

const Collapsible = React.forwardRef<
  HTMLDivElement,
  CollapsibleProps & React.HTMLAttributes<HTMLDivElement>
>(({ open, onOpenChange, children, ...props }, ref) => {
  return (
    <div ref={ref} data-state={open ? 'open' : 'closed'} {...props}>
      {children}
    </div>
  );
});
Collapsible.displayName = 'Collapsible';

interface CollapsibleTriggerProps {
  asChild?: boolean;
  children: React.ReactNode;
}

const CollapsibleTrigger = React.forwardRef<
  HTMLButtonElement,
  CollapsibleTriggerProps & React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ asChild, children, onClick, ...props }, ref) => {
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children as React.ReactElement<{ onClick?: React.MouseEventHandler }>, {
      onClick: (e: React.MouseEvent) => {
        onClick?.(e as React.MouseEvent<HTMLButtonElement>);
        (children as React.ReactElement<{ onClick?: React.MouseEventHandler }>).props.onClick?.(e);
      },
    });
  }

  return (
    <button ref={ref} type="button" onClick={onClick} {...props}>
      {children}
    </button>
  );
});
CollapsibleTrigger.displayName = 'CollapsibleTrigger';

interface CollapsibleContentProps {
  children: React.ReactNode;
}

const CollapsibleContent = React.forwardRef<
  HTMLDivElement,
  CollapsibleContentProps & React.HTMLAttributes<HTMLDivElement>
>(({ children, ...props }, ref) => {
  const parent = React.useContext(CollapsibleContext);

  if (!parent?.open) {
    return null;
  }

  return (
    <div ref={ref} {...props}>
      {children}
    </div>
  );
});
CollapsibleContent.displayName = 'CollapsibleContent';

// Context for open state
const CollapsibleContext = React.createContext<{ open?: boolean } | null>(null);

// Wrapper component that provides context
const CollapsibleRoot = React.forwardRef<
  HTMLDivElement,
  CollapsibleProps & React.HTMLAttributes<HTMLDivElement>
>(({ open, onOpenChange, children, ...props }, ref) => {
  return (
    <CollapsibleContext.Provider value={{ open }}>
      <div ref={ref} data-state={open ? 'open' : 'closed'} {...props}>
        {children}
      </div>
    </CollapsibleContext.Provider>
  );
});
CollapsibleRoot.displayName = 'CollapsibleRoot';

export { CollapsibleRoot as Collapsible, CollapsibleTrigger, CollapsibleContent };
