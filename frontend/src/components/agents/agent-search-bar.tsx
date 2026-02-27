"use client";

import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface AgentSearchBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
}

export function AgentSearchBar({ value, onChange, onSubmit }: AgentSearchBarProps) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit?.();
      }}
      className="relative"
    >
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        placeholder="Search agents by name, skill, or capability..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-11 pl-10"
      />
    </form>
  );
}
