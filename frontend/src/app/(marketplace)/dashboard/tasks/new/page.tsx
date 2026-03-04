"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
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
import { useCreateTask } from "@/lib/hooks/use-tasks";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import type { PaymentMethod } from "@/types/task";

export default function NewTaskPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedAgent = searchParams.get("agent") ?? "";

  const [agentId, setAgentId] = useState(preselectedAgent);
  const [skillId, setSkillId] = useState("");
  const [message, setMessage] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("credits");

  const { data: agentList } = useAgents({ per_page: 100, status: "active" });
  const { data: agent } = useAgent(agentId);
  const createTask = useCreateTask();

  // Auto-select first skill when agent changes
  const skills = agent?.skills ?? [];
  if (skills.length > 0 && !skillId && skills[0]) {
    setSkillId(skills[0].id);
  }

  const selectedSkill = skills.find((s) => s.id === skillId);
  const canSubmit = agentId && skillId && message.trim();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    try {
      const task = await createTask.mutateAsync({
        provider_agent_id: agentId,
        skill_id: skillId,
        messages: [
          {
            role: "user",
            parts: [{ type: "text", content: message.trim(), data: null, mime_type: null }],
          },
        ],
        payment_method: paymentMethod,
      });
      router.push(ROUTES.taskDetail(task.id));
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
        {/* Agent selector */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Agent</CardTitle>
            <CardDescription>Choose the agent to handle your task</CardDescription>
          </CardHeader>
          <CardContent>
            <Select
              value={agentId}
              onValueChange={(v) => {
                setAgentId(v);
                setSkillId("");
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
                    <span>~{formatCredits(selectedSkill.avg_credits)} credits</span>
                    {selectedSkill.avg_latency_ms > 0 && (
                      <span>~{Math.round(selectedSkill.avg_latency_ms / 1000)}s</span>
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
            <CardDescription>Describe what you need the agent to do</CardDescription>
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

        {createTask.isError && (
          <p className="text-center text-sm text-red-500">
            Failed to create task. Please try again.
          </p>
        )}
      </form>
    </div>
  );
}
