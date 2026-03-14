"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
  Sparkles,
  Star,
  ThumbsDown,
  ThumbsUp,
  Users,
  Zap,
} from "lucide-react";
import {
  useCustomAgent,
  useTryCustomAgent,
  useVoteCustomAgent,
} from "@/lib/hooks/use-custom-agents";
import { useAuth } from "@/lib/auth-context";
import { ROUTES } from "@/lib/constants";
import { formatRelativeTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";

export default function CommunityAgentDetailClient({ id }: { id: string }) {
  const pathname = usePathname();
  const realId = id === "__fallback" ? pathname.split("/").filter(Boolean).pop()! : id;

  const { user } = useAuth();
  const { data: agent, isLoading, error } = useCustomAgent(realId);
  const tryMutation = useTryCustomAgent(realId);
  const voteMutation = useVoteCustomAgent(realId);

  const [message, setMessage] = useState("");
  const [result, setResult] = useState<string | null>(null);

  async function handleTry() {
    if (!message.trim()) return;
    const res = await tryMutation.mutateAsync({ message: message.trim() });
    if (res.result) {
      setResult(res.result);
    } else if (res.task_id) {
      // Task dispatched to Creator Agent — redirect to task detail
      window.location.href = ROUTES.taskDetail(res.task_id);
    }
  }

  async function handleVote(vote: number) {
    if (!user) {
      window.location.href = `/login?redirect=${encodeURIComponent(pathname)}`;
      return;
    }
    await voteMutation.mutateAsync({ vote });
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center">
        <p className="text-muted-foreground">Agent not found</p>
        <a href="/community-agents">
          <Button variant="outline" className="mt-4 gap-1">
            <ArrowLeft className="h-4 w-4" /> Back to Community Agents
          </Button>
        </a>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      {/* Back link */}
      <a
        href="/community-agents"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Community Agents
      </a>

      {/* Header */}
      <div className="mt-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{agent.name}</h1>
              <Badge variant="secondary" className="text-[10px]">
                <Users className="mr-1 h-3 w-3" /> Community
              </Badge>
            </div>
            <p className="mt-2 text-muted-foreground">{agent.description}</p>
          </div>
        </div>

        {/* Stats */}
        <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
          <Badge variant="outline">{agent.category}</Badge>
          <span className="flex items-center gap-1">
            <Zap className="h-4 w-4" /> {agent.try_count} tries
          </span>
          <span className="flex items-center gap-1">
            <ThumbsUp className="h-4 w-4" /> {agent.upvote_count} upvotes
          </span>
          {agent.avg_rating > 0 && (
            <span className="flex items-center gap-1">
              <Star className="h-4 w-4 fill-amber-500 text-amber-500" />{" "}
              {agent.avg_rating.toFixed(1)}
            </span>
          )}
          <span>Created {formatRelativeTime(agent.created_at)}</span>
        </div>

        {/* Vote buttons */}
        <div className="mt-4 flex items-center gap-2">
          <Button
            variant={agent.user_vote === 1 ? "default" : "outline"}
            size="sm"
            onClick={() => handleVote(1)}
            disabled={voteMutation.isPending}
            className="gap-1"
          >
            <ThumbsUp className="h-4 w-4" /> Upvote
          </Button>
          <Button
            variant={agent.user_vote === -1 ? "destructive" : "outline"}
            size="sm"
            onClick={() => handleVote(-1)}
            disabled={voteMutation.isPending}
            className="gap-1"
          >
            <ThumbsDown className="h-4 w-4" /> Downvote
          </Button>
        </div>

        {/* Tags */}
        {agent.tags && agent.tags.length > 0 && (
          <div className="mt-4 flex flex-wrap gap-1">
            {agent.tags.map((tag) => (
              <Badge key={tag} variant="secondary" className="text-[10px]">
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Promoted notice */}
        {agent.status === "promoted" && agent.promoted_agent_id && (
          <div className="mt-4 rounded-lg border border-green-500/30 bg-green-500/5 p-4">
            <p className="text-sm text-green-400">
              A production version of this agent is now available!{" "}
              <a
                href={ROUTES.agentDetail(agent.promoted_agent_id)}
                className="font-medium underline"
              >
                View production agent
              </a>
            </p>
          </div>
        )}

        {/* Source query */}
        <div className="mt-6 rounded-lg border bg-muted/30 p-4">
          <p className="text-xs font-medium text-muted-foreground">Originally created for:</p>
          <p className="mt-1 text-sm italic">&quot;{agent.source_query}&quot;</p>
        </div>
      </div>

      {/* Try It panel */}
      <div className="mt-8">
        <h2 className="flex items-center gap-2 text-lg font-semibold">
          <Sparkles className="h-5 w-5 text-primary" />
          Try This Agent
        </h2>
        {user ? (
          <div className="mt-3 space-y-3">
            <Textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your task..."
              className="min-h-[100px] resize-none"
            />
            <div className="flex items-center gap-3">
              <Button
                onClick={handleTry}
                disabled={tryMutation.isPending || !message.trim()}
                className="gap-1"
              >
                {tryMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Zap className="h-4 w-4" />
                )}
                Run Task
              </Button>
              <span className="text-xs text-muted-foreground">3 credits</span>
            </div>
            {tryMutation.isError && (
              <p className="text-sm text-red-500">
                {(tryMutation.error as Error).message || "Task failed"}
              </p>
            )}
          </div>
        ) : (
          <div className="mt-3 rounded-lg border-2 border-dashed border-primary/20 p-6 text-center">
            <p className="text-sm text-muted-foreground">
              Sign in to try this agent
            </p>
            <a href={`/login?redirect=${encodeURIComponent(pathname)}`}>
              <Button className="mt-3">Sign In</Button>
            </a>
          </div>
        )}

        {/* Result display */}
        {result && (
          <div className="mt-6 rounded-lg border bg-card p-4">
            <h3 className="text-sm font-medium text-muted-foreground">Result</h3>
            <div className="mt-2 whitespace-pre-wrap text-sm">{result}</div>
          </div>
        )}
      </div>
    </div>
  );
}
