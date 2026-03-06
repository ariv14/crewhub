"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Search, Code2 } from "lucide-react";

interface ForkScreenProps {
  onSelectPath: (path: "use" | "build") => void;
}

export function ForkScreen({ onSelectPath }: ForkScreenProps) {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Welcome to CrewHub</h1>
        <p className="text-muted-foreground">
          How would you like to get started?
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card
          className="cursor-pointer transition-all hover:border-primary hover:shadow-md"
          onClick={() => onSelectPath("use")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") onSelectPath("use");
          }}
          data-testid="fork-use-agents"
        >
          <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
            <div className="rounded-full bg-primary/10 p-4">
              <Search className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-lg font-semibold">Use Agents</h2>
            <p className="text-sm text-muted-foreground">
              Find AI agents to help you with tasks
            </p>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer transition-all hover:border-primary hover:shadow-md"
          onClick={() => onSelectPath("build")}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") onSelectPath("build");
          }}
          data-testid="fork-build-agents"
        >
          <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
            <div className="rounded-full bg-primary/10 p-4">
              <Code2 className="h-8 w-8 text-primary" />
            </div>
            <h2 className="text-lg font-semibold">Build Agents</h2>
            <p className="text-sm text-muted-foreground">
              Register your agent on the marketplace
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
