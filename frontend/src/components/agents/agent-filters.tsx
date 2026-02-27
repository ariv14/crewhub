"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { CATEGORIES } from "@/lib/constants";
import { X } from "lucide-react";

export interface AgentFilterState {
  category: string;
  minReputation: string;
  maxCredits: string;
  status: string;
}

interface AgentFiltersProps {
  filters: AgentFilterState;
  onChange: (filters: AgentFilterState) => void;
}

export function AgentFilters({ filters, onChange }: AgentFiltersProps) {
  const hasFilters = Object.values(filters).some(Boolean);

  function update(key: keyof AgentFilterState, value: string) {
    onChange({ ...filters, [key]: value });
  }

  function clear() {
    onChange({ category: "", minReputation: "", maxCredits: "", status: "" });
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Filters</h3>
        {hasFilters && (
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={clear}>
            <X className="mr-1 h-3 w-3" />
            Clear
          </Button>
        )}
      </div>

      <Separator />

      <div className="space-y-3">
        <div className="space-y-1.5">
          <Label className="text-xs">Category</Label>
          <Select value={filters.category} onValueChange={(v) => update("category", v === "all" ? "" : v)}>
            <SelectTrigger className="h-8">
              <SelectValue placeholder="All categories" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All categories</SelectItem>
              {CATEGORIES.map((c) => (
                <SelectItem key={c.slug} value={c.slug}>
                  {c.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs">Min Reputation</Label>
          <Select value={filters.minReputation} onValueChange={(v) => update("minReputation", v === "any" ? "" : v)}>
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Any" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any</SelectItem>
              <SelectItem value="3">3.0+</SelectItem>
              <SelectItem value="4">4.0+</SelectItem>
              <SelectItem value="4.5">4.5+</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs">Max Credits/Task</Label>
          <Select value={filters.maxCredits} onValueChange={(v) => update("maxCredits", v === "any" ? "" : v)}>
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Any" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any</SelectItem>
              <SelectItem value="10">Up to 10</SelectItem>
              <SelectItem value="50">Up to 50</SelectItem>
              <SelectItem value="100">Up to 100</SelectItem>
              <SelectItem value="500">Up to 500</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs">Status</Label>
          <Select value={filters.status} onValueChange={(v) => update("status", v === "any" ? "" : v)}>
            <SelectTrigger className="h-8">
              <SelectValue placeholder="Active only" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="any">Any</SelectItem>
              <SelectItem value="active">Active</SelectItem>
              <SelectItem value="inactive">Inactive</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  );
}
