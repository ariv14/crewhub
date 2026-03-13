"use client";

import { useState } from "react";
import { Send, Gift, Sparkles, LogIn } from "lucide-react";
import Link from "next/link";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TaskMessageThread } from "@/components/tasks/task-message-thread";
import { TaskArtifactsDisplay } from "@/components/tasks/task-artifacts-display";
import { TaskProgressStepper } from "@/components/tasks/task-progress-stepper";
import { useCreateTask } from "@/lib/hooks/use-tasks";
import { useTask } from "@/lib/hooks/use-tasks";
import { useAuth } from "@/lib/auth-context";
import { useBalance } from "@/lib/hooks/use-credits";
import { cn } from "@/lib/utils";
import { guestTry } from "@/lib/api/tasks";
import type { Agent } from "@/types/agent";

interface TryAgentPanelProps {
  agent: Agent;
  initialMessage?: string;
}

export function TryAgentPanel({ agent, initialMessage }: TryAgentPanelProps) {
  const { user } = useAuth();
  const [input, setInput] = useState(initialMessage ?? "");
  const [selectedSkill, setSelectedSkill] = useState(
    agent.skills[0]?.id ?? ""
  );
  const [taskId, setTaskId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const selectedSkillObj = agent.skills.find((s) => s.id === selectedSkill);
  const defaultTier = agent.pricing.tiers.find((t) => t.is_default) ?? agent.pricing.tiers[0];
  const estimatedCost = defaultTier?.credits_per_unit ?? agent.pricing.credits ?? 0;
  const [guestLoading, setGuestLoading] = useState(false);
  const [guestResult, setGuestResult] = useState<{
    status: string;
    artifacts: any[];
    message?: string;
  } | null>(null);
  const createTask = useCreateTask();
  const { data: balance } = useBalance();
  const { data: task } = useTask(taskId ?? "");

  const hasUsedGuestTrial =
    typeof window !== "undefined" &&
    localStorage.getItem("guest_trial_used") === "true";

  const isWorking =
    task && ["submitted", "working", "input_required"].includes(task.status);
  const isDone =
    task &&
    ["completed", "failed", "canceled", "rejected"].includes(task.status);

  async function handleSend() {
    if (!input.trim() || !selectedSkill) return;
    setError(null);

    // Authenticated user — normal flow
    if (user) {
      try {
        const newTask = await createTask.mutateAsync({
          provider_agent_id: agent.id,
          skill_id: selectedSkill,
          messages: [
            {
              role: "user",
              parts: [
                {
                  type: "text",
                  content: input.trim(),
                  data: null,
                  mime_type: null,
                },
              ],
            },
          ],
        });
        setTaskId(newTask.id);
        setInput("");
      } catch {
        // error handled by mutation
      }
      return;
    }

    // Unauthenticated — one free guest trial
    if (hasUsedGuestTrial) return;

    setGuestLoading(true);
    try {
      const result = await guestTry({
        provider_agent_id: agent.id,
        skill_id: selectedSkill,
        message: input.trim(),
      });
      setGuestResult(result);
      localStorage.setItem("guest_trial_used", "true");
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to try agent"
      );
    } finally {
      setGuestLoading(false);
    }
  }

  function handleStarterClick(starter: string) {
    setInput(starter);
  }

  // Guest trial already used — show auth prompt
  const showGuestAuthGate = !user && hasUsedGuestTrial && !guestResult;

  return (
    <div className="space-y-4">
      {/* Skill selector */}
      {agent.skills.length > 1 && (
        <div className="space-y-1">
          <label className="text-sm font-medium">Skill</label>
          <Select value={selectedSkill} onValueChange={setSelectedSkill}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select a skill" />
            </SelectTrigger>
            <SelectContent>
              {agent.skills.map((skill) => (
                <SelectItem key={skill.id} value={skill.id}>
                  {skill.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Conversation starters */}
      {!taskId && !guestResult && agent.conversation_starters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {agent.conversation_starters.map((starter) => (
            <Badge
              key={starter}
              variant="outline"
              className="cursor-pointer transition-colors hover:bg-primary/10"
              onClick={() => handleStarterClick(starter)}
            >
              {starter}
            </Badge>
          ))}
        </div>
      )}

      {/* Free preview hint for unauthenticated users */}
      {!user && !hasUsedGuestTrial && !guestResult && (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Sparkles className="h-3 w-3 text-primary" />
          Free preview — no account needed
        </div>
      )}

      {/* Authenticated task results */}
      {task && (
        <div className="rounded-lg border p-4 space-y-4">
          <TaskMessageThread messages={task.messages} />
          {isWorking && task && (
            <TaskProgressStepper
              status={task.status}
              statusHistory={task.status_history ?? null}
              createdAt={task.created_at}
            />
          )}
          {isDone && task.artifacts && task.artifacts.length > 0 && (
            <TaskArtifactsDisplay artifacts={task.artifacts} />
          )}
          {task.status === "failed" && (
            <div className="mt-3 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              Task failed. Try again with different input.
            </div>
          )}
        </div>
      )}

      {/* Guest trial result */}
      {guestResult && (
        <div className="space-y-4">
          {/* Show the user's message */}
          <div className="rounded-lg border p-4 space-y-3">
            <div className="text-sm text-muted-foreground">
              {input || "Your message"}
            </div>
            {guestResult.message && (
              <div className="whitespace-pre-wrap text-sm">
                {guestResult.message}
              </div>
            )}
            {!guestResult.message &&
              guestResult.artifacts.length > 0 && (
                <TaskArtifactsDisplay artifacts={guestResult.artifacts} />
              )}
            {guestResult.status === "failed" && (
              <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                Agent couldn&apos;t complete this request. Try a different message after signing up.
              </div>
            )}
          </div>

          {/* Signup CTA */}
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-center space-y-2">
            <div className="flex items-center justify-center gap-2 text-sm font-medium">
              <Gift className="h-4 w-4 text-primary" />
              You just tried an AI agent for free!
            </div>
            <p className="text-xs text-muted-foreground">
              Sign up now and get 250 credits to try premium agents and team
              mode.
            </p>
            <Link
              href={`/login?redirect=${encodeURIComponent(`/agents/${agent.id}/?tab=try`)}`}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Create Free Account
            </Link>
          </div>
        </div>
      )}

      {/* Error — premium agent gate or generic */}
      {error && (
        error.includes("free community agents") ? (
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 space-y-2">
            <div className="flex items-center gap-2 text-sm font-medium">
              <LogIn className="h-4 w-4 text-primary" />
              This is a premium agent
            </div>
            <p className="text-xs text-muted-foreground">
              Guest trial is only available for free agents. Sign up to get 250 free credits and try premium agents.
            </p>
            <Link
              href={`/login?redirect=${encodeURIComponent(`/agents/${agent.id}/?tab=try`)}`}
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Create Free Account
            </Link>
          </div>
        ) : (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
            {error}
          </div>
        )
      )}

      {/* Input area — varies by auth state */}
      {showGuestAuthGate ? (
        <div className="rounded-lg border border-primary/20 bg-primary/5 p-4 text-center space-y-2">
          <div className="flex items-center justify-center gap-2 text-sm font-medium">
            <Gift className="h-4 w-4 text-primary" />
            Want to try more agents?
          </div>
          <p className="text-xs text-muted-foreground">
            Sign up now and get <span className="font-semibold text-foreground">250 free credits</span> to try premium agents and team mode.
          </p>
          <a
            href={`/login?redirect=${encodeURIComponent(`/agents/${agent.id}/?tab=try`)}`}
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <LogIn className="h-3.5 w-3.5" />
            Create Free Account
          </a>
        </div>
      ) : !guestResult ? (
        <>
        {user && estimatedCost > 0 && !taskId && !guestResult && (
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Estimated cost: <span className="font-medium text-foreground">{estimatedCost} credits</span></span>
            {balance && (
              <span>
                Balance: <span className={cn("font-medium", balance.available < estimatedCost ? "text-destructive" : "text-foreground")}>
                  {balance.available} credits
                </span>
              </span>
            )}
          </div>
        )}
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Type a message..."
            disabled={createTask.isPending || !!isWorking || guestLoading}
          />
          <Button
            onClick={handleSend}
            disabled={
              !input.trim() ||
              !selectedSkill ||
              createTask.isPending ||
              !!isWorking ||
              guestLoading
            }
            title={isDone ? "Send another message" : undefined}
            size="icon"
          >
            {createTask.isPending || guestLoading ? (
              <SpinningLogo spinning size="sm" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        </>
      ) : null}
    </div>
  );
}
