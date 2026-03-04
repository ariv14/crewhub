"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Hand,
  Loader2,
  Search,
  Send,
  Sparkles,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
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
import { useCreateTask, useSuggestDelegation } from "@/lib/hooks/use-tasks";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import type { PaymentMethod, SkillSuggestion } from "@/types/task";

type DelegationMode = "auto" | "manual";

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

// --- Confidence bar color helper ---
function confidenceColor(c: number) {
  if (c >= 0.7) return "bg-green-500";
  if (c >= 0.3) return "bg-yellow-500";
  return "bg-red-400";
}

function confidenceLabel(c: number) {
  if (c >= 0.7) return "Strong match";
  if (c >= 0.3) return "Moderate match";
  return "Weak match";
}

// --- Suggestion Card ---
function SuggestionCard({
  suggestion,
  onSelect,
  isCreating,
}: {
  suggestion: SkillSuggestion;
  onSelect: () => void;
  isCreating: boolean;
}) {
  return (
    <Card
      className={`transition-colors ${suggestion.low_confidence ? "border-red-200 dark:border-red-900" : "hover:border-primary/50"}`}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="truncate font-medium">{suggestion.agent.name}</p>
              <Badge variant="secondary" className="shrink-0 text-xs">
                {suggestion.skill.name}
              </Badge>
            </div>
            <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
              {suggestion.skill.description}
            </p>
            <div className="mt-2 flex items-center gap-3">
              <div className="flex items-center gap-2 flex-1 max-w-48">
                <Progress
                  value={suggestion.confidence * 100}
                  className="h-2"
                />
                <span className="shrink-0 text-xs text-muted-foreground">
                  {Math.round(suggestion.confidence * 100)}%
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {confidenceLabel(suggestion.confidence)}
              </span>
            </div>
          </div>
          <Button
            size="sm"
            onClick={onSelect}
            disabled={isCreating}
          >
            {isCreating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <>
                Use this
                <ArrowRight className="ml-1 h-3 w-3" />
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// --- Manual mode guardrail badge ---
function MatchGuardrail({
  suggestion,
  currentAgentId,
  currentSkillId,
  onSwitch,
}: {
  suggestion: SkillSuggestion;
  currentAgentId: string;
  currentSkillId: string;
  onSwitch: (agentId: string, skillId: string) => void;
}) {
  const sameAgent = suggestion.agent.id === currentAgentId;
  const sameSkill = suggestion.skill.id === currentSkillId;

  if (sameSkill) {
    return (
      <div className="flex items-center gap-2 rounded-md bg-green-50 p-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
        <CheckCircle2 className="h-4 w-4 shrink-0" />
        Good match for this skill
      </div>
    );
  }

  if (sameAgent) {
    return (
      <button
        type="button"
        onClick={() => onSwitch(suggestion.agent.id, suggestion.skill.id)}
        className="flex w-full items-center gap-2 rounded-md bg-yellow-50 p-2 text-left text-sm text-yellow-700 transition-colors hover:bg-yellow-100 dark:bg-yellow-950 dark:text-yellow-300 dark:hover:bg-yellow-900"
      >
        <AlertTriangle className="h-4 w-4 shrink-0" />
        <span>
          Consider: <strong>{suggestion.skill.name}</strong> might be a better
          fit
        </span>
      </button>
    );
  }

  return (
    <button
      type="button"
      onClick={() => onSwitch(suggestion.agent.id, suggestion.skill.id)}
      className="flex w-full items-center gap-2 rounded-md bg-orange-50 p-2 text-left text-sm text-orange-700 transition-colors hover:bg-orange-100 dark:bg-orange-950 dark:text-orange-300 dark:hover:bg-orange-900"
    >
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>
        Better match: <strong>{suggestion.agent.name}</strong> &rarr;{" "}
        <strong>{suggestion.skill.name}</strong>
      </span>
    </button>
  );
}

function NewTaskForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedAgent = searchParams.get("agent") ?? "";

  // Mode: auto (message-first) or manual (agent-first)
  const [mode, setMode] = useState<DelegationMode>(
    preselectedAgent ? "manual" : "auto"
  );

  // Shared state
  const [message, setMessage] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("credits");

  // Manual mode state
  const [agentId, setAgentId] = useState(preselectedAgent);
  const [skillId, setSkillId] = useState("");

  // Auto mode state
  const [maxCredits, setMaxCredits] = useState<string>("");

  // Suggestion state
  const suggest = useSuggestDelegation();
  const [guardrailSuggestion, setGuardrailSuggestion] =
    useState<SkillSuggestion | null>(null);

  const createTask = useCreateTask();
  const { data: agentList } = useAgents({ per_page: 100, status: "active" });
  const { data: agent } = useAgent(agentId);

  // Auto-select first skill when agent changes
  const skills = agent?.skills ?? [];
  if (skills.length > 0 && !skillId && skills[0]) {
    setSkillId(skills[0].id);
  }
  const selectedSkill = skills.find((s) => s.id === skillId);

  // --- Auto mode: find best agent ---
  async function handleAutoSearch() {
    if (!message.trim()) return;
    suggest.mutate({
      message: message.trim(),
      max_credits: maxCredits ? parseFloat(maxCredits) : undefined,
      limit: 3,
    });
  }

  // --- Auto mode: use a suggestion ---
  async function handleSelectSuggestion(s: SkillSuggestion) {
    try {
      const task = await createTask.mutateAsync({
        provider_agent_id: s.agent.id,
        skill_id: s.skill.id,
        messages: [
          {
            role: "user",
            parts: [
              { type: "text", content: message.trim(), data: null, mime_type: null },
            ],
          },
        ],
        payment_method: paymentMethod,
      });
      router.push(ROUTES.taskDetail(task.id));
    } catch {
      // error handled by mutation state
    }
  }

  // --- Manual mode: submit ---
  const canSubmitManual = agentId && skillId && message.trim();

  async function handleManualSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmitManual) return;

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
        validate_match: true,
      });
      router.push(ROUTES.taskDetail(task.id));
    } catch {
      // error handled by mutation state
    }
  }

  // --- Manual mode guardrail: debounced check ---
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const checkGuardrail = useCallback(
    (msg: string, sId: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      setGuardrailSuggestion(null);

      if (msg.length < 20 || !sId) return;

      debounceRef.current = setTimeout(async () => {
        try {
          const result = await suggest.mutateAsync({
            message: msg,
            limit: 1,
          });
          if (result.suggestions.length > 0) {
            setGuardrailSuggestion(result.suggestions[0]);
          }
        } catch {
          // non-critical
        }
      }, 800);
    },
    [suggest]
  );

  // Trigger guardrail when message or skill changes in manual mode
  useEffect(() => {
    if (mode === "manual") {
      checkGuardrail(message, skillId);
    }
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [message, skillId, mode]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSwitchToSuggested(newAgentId: string, newSkillId: string) {
    setAgentId(newAgentId);
    setSkillId(newSkillId);
    setGuardrailSuggestion(null);
  }

  const allLowConfidence =
    suggest.data?.suggestions?.every((s) => s.low_confidence) ?? false;

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

      {/* Mode toggle */}
      <div className="mb-6 flex gap-2">
        <Button
          variant={mode === "auto" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("auto")}
        >
          <Sparkles className="mr-2 h-4 w-4" />
          Auto
        </Button>
        <Button
          variant={mode === "manual" ? "default" : "outline"}
          size="sm"
          onClick={() => setMode("manual")}
        >
          <Hand className="mr-2 h-4 w-4" />
          Manual
        </Button>
        <span className="self-center text-xs text-muted-foreground">
          {mode === "auto"
            ? "Let the system find the best agent"
            : "Choose agent & skill yourself"}
        </span>
      </div>

      {/* ============ AUTO MODE ============ */}
      {mode === "auto" && (
        <div className="space-y-6">
          {/* Message */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">What do you need?</CardTitle>
              <CardDescription>
                Describe your task and we&apos;ll find the best agent
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="e.g., Build me a responsive landing page with a hero section..."
                rows={4}
              />
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-2">
                  <Label htmlFor="max-credits" className="shrink-0 text-sm">
                    Max budget
                  </Label>
                  <Input
                    id="max-credits"
                    type="number"
                    min="0"
                    step="0.1"
                    placeholder="No limit"
                    value={maxCredits}
                    onChange={(e) => setMaxCredits(e.target.value)}
                    className="w-28"
                  />
                  <span className="text-xs text-muted-foreground">credits</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <Button
            className="w-full"
            onClick={handleAutoSearch}
            disabled={!message.trim() || suggest.isPending}
          >
            {suggest.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Finding best agents...
              </>
            ) : (
              <>
                <Search className="mr-2 h-4 w-4" />
                Find Best Agent
              </>
            )}
          </Button>

          {/* Suggestion results */}
          {suggest.data && (
            <div className="space-y-3">
              {suggest.data.hint && (
                <p className="text-xs text-muted-foreground">
                  {suggest.data.hint}
                </p>
              )}

              {allLowConfidence && (
                <div className="flex items-center gap-2 rounded-md bg-yellow-50 p-3 text-sm text-yellow-700 dark:bg-yellow-950 dark:text-yellow-300">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  No strong matches found. Try being more specific or switch to
                  manual mode.
                </div>
              )}

              {suggest.data.suggestions.length === 0 && (
                <p className="text-center text-sm text-muted-foreground">
                  No matching agents found. Try a different description.
                </p>
              )}

              {suggest.data.suggestions.map((s) => (
                <SuggestionCard
                  key={`${s.agent.id}-${s.skill.id}`}
                  suggestion={s}
                  onSelect={() => handleSelectSuggestion(s)}
                  isCreating={createTask.isPending}
                />
              ))}
            </div>
          )}

          {suggest.isError && (
            <p className="text-center text-sm text-red-500">
              Failed to get suggestions. Please try again.
            </p>
          )}

          {createTask.isError && (
            <p className="text-center text-sm text-red-500">
              Failed to create task. Please try again.
            </p>
          )}
        </div>
      )}

      {/* ============ MANUAL MODE ============ */}
      {mode === "manual" && (
        <form onSubmit={handleManualSubmit} className="space-y-6">
          {/* Agent selector */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Agent</CardTitle>
              <CardDescription>
                Choose the agent to handle your task
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Select
                value={agentId}
                onValueChange={(v) => {
                  setAgentId(v);
                  setSkillId("");
                  setGuardrailSuggestion(null);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select an agent" />
                </SelectTrigger>
                <SelectContent>
                  {(agentList?.agents ?? []).map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      {a.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {agent && (
                <p className="mt-2 text-sm text-muted-foreground">
                  {agent.description}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Skill selector */}
          {skills.length > 0 && (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Skill</CardTitle>
                <CardDescription>Select a specific capability</CardDescription>
              </CardHeader>
              <CardContent>
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

                {selectedSkill && (
                  <div className="mt-2 space-y-1">
                    <p className="text-sm text-muted-foreground">
                      {selectedSkill.description}
                    </p>
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

          {/* Message */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Message</CardTitle>
              <CardDescription>
                Describe what you need the agent to do
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Conversation starters */}
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
                placeholder="e.g., Summarize the latest earnings report for AAPL..."
                rows={4}
              />

              {/* Guardrail badge */}
              {guardrailSuggestion && agentId && skillId && (
                <MatchGuardrail
                  suggestion={guardrailSuggestion}
                  currentAgentId={agentId}
                  currentSkillId={skillId}
                  onSwitch={handleSwitchToSuggested}
                />
              )}
            </CardContent>
          </Card>

          {/* Payment method */}
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

          {/* Submit */}
          <Button
            type="submit"
            className="w-full"
            disabled={!canSubmitManual || createTask.isPending}
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

          {createTask.isError && (
            <p className="text-center text-sm text-red-500">
              Failed to create task. Please try again.
            </p>
          )}
        </form>
      )}
    </div>
  );
}
