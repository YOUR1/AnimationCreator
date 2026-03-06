"use client";

import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CreditBadge } from "@/components/shared/CreditBadge";
import { UserDropdown } from "./UserDropdown";
import { useCredits } from "@/hooks/useCredits";
import type { User } from "@/types";

interface HeaderProps {
  user: User;
  onMenuClick?: () => void;
}

export function Header({ user, onMenuClick }: HeaderProps) {
  const { credits, isLoading } = useCredits();

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background px-4 md:px-6">
      {/* Mobile menu button */}
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden"
        onClick={onMenuClick}
      >
        <Menu className="h-5 w-5" />
        <span className="sr-only">Toggle menu</span>
      </Button>

      {/* Spacer for desktop */}
      <div className="hidden md:block" />

      {/* Right side items */}
      <div className="flex items-center gap-4">
        <CreditBadge credits={credits} isLoading={isLoading} />
        <UserDropdown user={user} />
      </div>
    </header>
  );
}
