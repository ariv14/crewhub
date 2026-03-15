// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import Link from "next/link";
import { UsersRound, Plus, Trash2, Globe, Lock, Play, X, ArrowRight } from "lucide-react";
import { useMyCrews, useDeleteCrew } from "@/lib/hooks/use-crews";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/utils";
import { EmptyState } from "@/components/shared/empty-state";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useState } from "react";
import type { Crew } from "@/types/crew";

function CrewCard({ crew, onDelete }: { crew: Crew; onDelete: (id: string) => void }) {
  return (
    <div className="group relative rounded-xl border bg-card p-5 transition-all hover:border-primary/30 hover:shadow-sm">
      <a href={ROUTES.crewDetail(crew.id)} className="absolute inset-0 z-0" />

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-lg">
            {crew.icon || "👥"}
          </div>
          <div>
            <h3 className="font-semibold">{crew.name}</h3>
            <p className="text-xs text-muted-foreground">
              {crew.members.length} member{crew.members.length !== 1 ? "s" : ""}
            </p>
          </div>
        </div>

        <div className="relative z-10 flex items-center gap-1">
          <Badge variant="outline" className="text-[10px]">
            {crew.is_public ? (
              <><Globe className="mr-1 h-3 w-3" />Public</>
            ) : (
              <><Lock className="mr-1 h-3 w-3" />Private</>
            )}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 opacity-0 group-hover:opacity-100"
            onClick={(e) => { e.preventDefault(); onDelete(crew.id); }}
          >
            <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
          </Button>
        </div>
      </div>

      {crew.description && (
        <p className="mt-3 line-clamp-2 text-sm text-muted-foreground">
          {crew.description}
        </p>
      )}

      {/* Member avatars */}
      <div className="mt-4 flex flex-wrap gap-1.5">
        {crew.members.map((m) => (
          <div
            key={m.id}
            className="flex items-center gap-1 rounded-full border bg-muted/50 px-2 py-0.5 text-[10px]"
            title={`${m.agent?.name} — ${m.skill?.name}`}
          >
            <span>{m.agent?.name?.charAt(0) || "?"}</span>
            <span className="text-muted-foreground">{m.skill?.name || "skill"}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
        <span>Updated {formatRelativeTime(crew.updated_at)}</span>
        <Button
          variant="outline"
          size="sm"
          className="relative z-10 h-7 gap-1 text-xs"
          asChild
        >
          <a href={ROUTES.crewDetail(crew.id)}>
            <Play className="h-3 w-3" />
            Run
          </a>
        </Button>
      </div>
    </div>
  );
}

export default function MyCrewsPage() {
  const { data, isLoading } = useMyCrews();
  const deleteCrew = useDeleteCrew();
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [showDeprecationBanner, setShowDeprecationBanner] = useState(true);

  const crews = data?.crews ?? [];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Crews</h1>
          <p className="mt-1 text-muted-foreground">
            Saved agent teams you can re-run anytime
          </p>
        </div>
        <Button asChild>
          <Link href={ROUTES.teamMode}>
            <Plus className="mr-2 h-4 w-4" />
            Build New Crew
          </Link>
        </Button>
      </div>

      {showDeprecationBanner && (
        <div className="mt-4 flex items-start gap-3 rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3">
          <div className="min-w-0 flex-1 text-sm">
            <p className="text-amber-600 dark:text-amber-400">
              <strong>Crews are becoming Workflows</strong> — convert your crews for sequential chaining, per-step instructions, and run history.
            </p>
            <a
              href="/dashboard/workflows"
              className="mt-1 inline-flex items-center gap-1 text-xs font-medium text-amber-600 hover:text-amber-700 dark:text-amber-400 dark:hover:text-amber-300"
            >
              Learn about Workflows <ArrowRight className="h-3 w-3" />
            </a>
          </div>
          <button
            onClick={() => setShowDeprecationBanner(false)}
            className="shrink-0 rounded p-0.5 text-amber-600/60 hover:text-amber-600 dark:text-amber-400/60 dark:hover:text-amber-400"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <div className="mt-6">
        {!isLoading && crews.length === 0 ? (
          <EmptyState
            icon={UsersRound}
            title="No saved crews yet"
            description="Assemble a team on the Team page, then save it as a crew for easy re-use."
            action={
              <Button asChild>
                <Link href={ROUTES.teamMode}>Assemble Team</Link>
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {crews.map((crew) => (
              <CrewCard key={crew.id} crew={crew} onDelete={setDeleteTarget} />
            ))}
          </div>
        )}
      </div>

      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Delete Crew"
        description="This will permanently delete this crew. This action cannot be undone."
        confirmLabel="Delete"
        variant="destructive"
        loading={deleteCrew.isPending}
        onConfirm={() => {
          if (deleteTarget) {
            deleteCrew.mutate(deleteTarget, {
              onSuccess: () => setDeleteTarget(null),
              onError: () => setDeleteTarget(null),
            });
          }
        }}
      />
    </div>
  );
}
