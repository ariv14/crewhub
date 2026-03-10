"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Loader2,
  Search,
  Send,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAgents, useAgent } from "@/lib/hooks/use-agents";
import { useCreateTask, useCancelTask } from "@/lib/hooks/use-tasks";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import type { PaymentMethod } from "@/types/task";
import type { Agent } from "@/types/agent";
import { toast } from "sonner";

export default function NewTaskPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-2xl">
          <h1 className="text-2xl font-bold">Create Task</h1>
          <p className="mt-1 text-muted-foreground">Loading...</p>
        </div>
      }
    >
      <NewTaskForm />
    </Suspense>
  );
}

function AgentSearchCard({
  agent,
  onSelect,
}: {
  agent: Agent;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="w-full rounded-lg border bg-card p-4 text-left transition-colors hover:border-primary/50 hover:bg-accent/50"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate font-medium">{agent.name}</p>
          <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
            {agent.description}
          </p>
          {agent.skills.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {agent.skills.slice(0, 4).map((skill) => (
                <Badge key={skill.id} variant="secondary" className="text-xs">
                  {skill.name}
                </Badge>
              ))}
              {agent.skills.length > 4 && (
                <Badge variant="outline" className="text-xs">
                  +{agent.skills.length - 4} more
                </Badge>
              )}
            </div>
          )}
          {(agent.success_rate > 0.95 || (agent.avg_latency_ms > 0 && agent.avg_latency_ms < 5000) || agent.total_tasks_completed > 10) && (
            <div className="mt-2 flex flex-wrap gap-1">
              {agent.success_rate > 0.95 && (
                <Badge variant="outline" className="text-[10px] border-green-500/30 text-green-500">
                  {Math.round(agent.success_rate * 100)}% success
                </Badge>
              )}
              {agent.avg_latency_ms > 0 && agent.avg_latency_ms < 5000 && (
                <Badge variant="outline" className="text-[10px] border-blue-500/30 text-blue-500">
                  Fast
                </Badge>
              )}
              {agent.total_tasks_completed > 10 && (
                <Badge variant="outline" className="text-[10px] border-purple-500/30 text-purple-500">
                  {agent.total_tasks_completed} tasks
                </Badge>
              )}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

function NewTaskForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const preselectedAgent = searchParams.get("agent") ?? "";
  const preselectedSkill = searchParams.get("skill") ?? "";
  const preselectedMessage = searchParams.get("message") ?? "";

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Selection state
  const [agentId, setAgentId] = useState(preselectedAgent);
  const [skillId, setSkillId] = useState(preselectedSkill);
  const [message, setMessage] = useState(preselectedMessage);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("credits");

  const createTask = useCreateTask();
  const cancelTask = useCancelTask();
  const { data: agent } = useAgent(agentId);

  // Default agent listing (always loaded)
  const { data: defaultResults, isLoading: isLoadingDefaults } = useAgents(
    { per_page: 20, status: "active" }
  );

  // Search agents (only when there's a debounced query)
  const { data: searchResults, isFetching: isSearching } = useAgents(
    debouncedQuery
      ? { q: debouncedQuery, per_page: 10, status: "active" }
      : undefined
  );

  // Show search results when searching, otherwise show all agents
  const displayAgents = debouncedQuery
    ? searchResults?.agents ?? []
    : defaultResults?.agents ?? [];

  // Debounce search input
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!searchQuery.trim()) {
      setDebouncedQuery("");
      return;
    }
    debounceRef.current = setTimeout(() => {
      setDebouncedQuery(searchQuery.trim());
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery]);

  // Auto-select first skill when agent changes
  const skills = agent?.skills ?? [];
  useEffect(() => {
    if (skills.length === 1 && skills[0]) {
      setSkillId(skills[0].id);
    } else if (skills.length === 0) {
      setSkillId("");
    }
  }, [agent?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const selectedSkill = skills.find((s) => s.id === skillId);

  function handleSelectAgent(selectedAgent: Agent) {
    setAgentId(selectedAgent.id);
    setSkillId("");
    setSearchQuery("");
    setDebouncedQuery("");
  }

  function handleClearAgent() {
    setAgentId("");
    setSkillId("");
  }

  const canSubmit = agentId && skillId && message.trim();

  async function handleSubmit(e: React.FormEvent, confirmed = false) {
    e.preventDefault();
    if (!canSubmit) return;

    try {
      const task = await createTask.mutateAsync({
        provider_agent_id: agentId,
        skill_id: skillId,
        messages: [
          {
            role: "user",
            parts: [
              { type: "text", content: message.trim(), data: null, mime_type: null },
            ],
          },
        ],
        payment_method: paymentMethod,
        confirmed,
      });

      // High-cost approval: show confirmation dialog instead of navigating
      if (task.status === "pending_approval") {
        sessionStorage.setItem("nav_task_id", task.id);
        window.location.href = ROUTES.taskDetail(task.id);
        return;
      }

      // Normal flow: show undo toast with 5s grace period
      sessionStorage.setItem("nav_task_id", task.id);
      const taskId = task.id;
      toast("Task created", {
        description: `Dispatching to ${agent?.name ?? "agent"} in 5 seconds...`,
        action: {
          label: "Undo",
          onClick: () => {
            cancelTask.mutate(taskId);
            toast.success("Task canceled");
          },
        },
        duration: 5000,
      });
      // Navigate after a short delay so user sees the toast
      setTimeout(() => {
        window.location.href = ROUTES.taskDetail(taskId);
      }, 1000);
    } catch {
      // error handled by mutation state
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild className="mb-2">
          <Link href={ROUTES.myTasks}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Tasks
          </Link>
        </Button>
        <h1 className="text-2xl font-bold">Create Task</h1>
        <p className="mt-1 text-muted-foreground">
          Delegate a new task to an agent
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Step 1: Search / Select Agent */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Agent</CardTitle>
            <CardDescription>
              {agentId
                ? "Selected agent for your task"
                : "Search for an agent to handle your task"}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {!agentId ? (
              <>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search agents by name or description..."
                    className="pl-9"
                  />
                </div>

                {(isSearching || isLoadingDefaults) && (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                  </div>
                )}

                {!isSearching && !isLoadingDefaults && (
                  <div className="space-y-2">
                    {displayAgents.length === 0 ? (
                      <p className="py-4 text-center text-sm text-muted-foreground">
                        {debouncedQuery
                          ? <>No agents found for &ldquo;{debouncedQuery}&rdquo;</>
                          : "No agents available"}
                      </p>
                    ) : (
                      displayAgents.map((a) => (
                        <AgentSearchCard
                          key={a.id}
                          agent={a}
                          onSelect={() => handleSelectAgent(a)}
                        />
                      ))
                    )}
                  </div>
                )}
              </>
            ) : (
              <div className="flex items-start justify-between gap-3 rounded-lg border bg-accent/30 p-3">
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{agent?.name ?? "Loading..."}</p>
                  {agent?.description && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {agent.description}
                    </p>
                  )}
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleClearAgent}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Step 2: Skill selector (shown after agent selected) */}
        {agentId && skills.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Skill</CardTitle>
              <CardDescription>Select a specific capability</CardDescription>
            </CardHeader>
            <CardContent>
              {skills.length === 1 ? (
                <div className="space-y-1">
                  <p className="font-medium text-sm">{skills[0].name}</p>
                  <p className="text-sm text-muted-foreground">
                    {skills[0].description}
                  </p>
                </div>
              ) : (
                <Select value={skillId} onValueChange={setSkillId}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select a skill" />
                  </SelectTrigger>
                  <SelectContent>
                    {skills.map((skill) => (
                      <SelectItem key={skill.id} value={skill.id}>
                        {skill.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {selectedSkill && (
                <div className="mt-2 space-y-1">
                  {skills.length > 1 && (
                    <p className="text-sm text-muted-foreground">
                      {selectedSkill.description}
                    </p>
                  )}
                  <div className="flex gap-2 text-xs text-muted-foreground">
                    <span>
                      ~{formatCredits(selectedSkill.avg_credits)} credits
                    </span>
                    {selectedSkill.avg_latency_ms > 0 && (
                      <span>
                        ~{Math.round(selectedSkill.avg_latency_ms / 1000)}s
                      </span>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Step 3: Message */}
        {agentId && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Message</CardTitle>
              <CardDescription>
                Describe what you need the agent to do
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {agent && agent.conversation_starters.length > 0 && !message && (
                <div className="flex flex-wrap gap-2">
                  {agent.conversation_starters.map((starter) => (
                    <Badge
                      key={starter}
                      variant="outline"
                      className="cursor-pointer transition-colors hover:bg-primary/10"
                      onClick={() => setMessage(starter)}
                    >
                      {starter}
                    </Badge>
                  ))}
                </div>
              )}

              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder={
                  selectedSkill?.examples?.[0]?.input
                    ? `e.g., ${selectedSkill.examples[0].input}`
                    : "e.g., Summarize the latest earnings report for AAPL..."
                }
                rows={4}
              />
            </CardContent>
          </Card>
        )}

        {/* Step 4: Payment */}
        {agentId && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Payment</CardTitle>
              <CardDescription>How to pay for this task</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <Label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="payment"
                    value="credits"
                    checked={paymentMethod === "credits"}
                    onChange={() => setPaymentMethod("credits")}
                    className="accent-primary"
                  />
                  <span className="text-sm">Platform Credits</span>
                </Label>
                {agent?.accepted_payment_methods?.includes("x402") && (
                  <Label className="flex cursor-pointer items-center gap-2">
                    <input
                      type="radio"
                      name="payment"
                      value="x402"
                      checked={paymentMethod === "x402"}
                      onChange={() => setPaymentMethod("x402")}
                      className="accent-primary"
                    />
                    <span className="text-sm">x402 (Crypto)</span>
                  </Label>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Submit */}
        {agentId && (
          <Button
            type="submit"
            className="w-full"
            disabled={!canSubmit || createTask.isPending}
          >
            {createTask.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Task...
              </>
            ) : (
              <>
                <Send className="mr-2 h-4 w-4" />
                Create Task
              </>
            )}
          </Button>
        )}

        {createTask.isError && (
          <p className="text-center text-sm text-red-500">
            Failed to create task. Please try again.
          </p>
        )}
      </form>
    </div>
  );
}
