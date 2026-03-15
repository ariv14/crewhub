// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { ArrowRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const SEMVER_RE = /^(\d+)\.(\d+)\.(\d+)$/;

function parseSemver(v: string): [number, number, number] | null {
  const m = SEMVER_RE.exec(v.trim());
  if (!m) return null;
  return [Number(m[1]), Number(m[2]), Number(m[3])];
}

function bump(
  v: string,
  type: "patch" | "minor" | "major"
): string {
  const parts = parseSemver(v);
  if (!parts) return v;
  const [major, minor, patch] = parts;
  switch (type) {
    case "patch":
      return `${major}.${minor}.${patch + 1}`;
    case "minor":
      return `${major}.${minor + 1}.0`;
    case "major":
      return `${major + 1}.0.0`;
  }
}

const BUMP_TYPES = [
  { type: "patch" as const, label: "Patch", hint: "Bug fixes" },
  { type: "minor" as const, label: "Minor", hint: "New features" },
  { type: "major" as const, label: "Major", hint: "Breaking changes" },
];

export function VersionBumper({
  value,
  onChange,
  detectedVersion,
}: {
  value: string;
  onChange: (v: string) => void;
  detectedVersion?: string | null;
}) {
  const isSemver = parseSemver(value) !== null;
  const showDrift =
    detectedVersion && detectedVersion !== value && parseSemver(detectedVersion);

  return (
    <div className="space-y-2" data-testid="version-bumper">
      <Label>Release Version</Label>
      <div className="flex items-center gap-2">
        <Input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-28 font-mono"
          placeholder="1.0.0"
        />
        {isSemver && (
          <div className="flex gap-1" data-testid="version-bump-buttons">
            {BUMP_TYPES.map(({ type, label, hint }) => (
              <Button
                key={type}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onChange(bump(value, type))}
                className={cn(
                  "text-xs",
                  type === "major" && "border-destructive/30 text-destructive hover:bg-destructive/10"
                )}
                title={`${hint} → ${bump(value, type)}`}
              >
                {label}
              </Button>
            ))}
          </div>
        )}
      </div>
      {isSemver && (
        <p className="text-[11px] text-muted-foreground">
          Bump when you deploy changes. Marketplace users see this version.
        </p>
      )}
      {!isSemver && value && (
        <p className="text-[11px] text-amber-500">
          Not a semver format (x.y.z). Bump buttons disabled.
        </p>
      )}
      {showDrift && (
        <p
          className="flex items-center gap-1 text-[11px] text-amber-500"
          data-testid="version-drift-warning"
        >
          <ArrowRight className="h-3 w-3" />
          Agent card reports{" "}
          <span className="font-mono font-medium">{detectedVersion}</span>
          {" — "}marketplace shows{" "}
          <span className="font-mono font-medium">{value}</span>
        </p>
      )}
    </div>
  );
}
