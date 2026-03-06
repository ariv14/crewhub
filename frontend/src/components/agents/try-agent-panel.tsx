"use client";

import { useState } from "react";
import { Send } from "lucide-react";
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
import { useCreateTask } from "@/lib/hooks/use-tasks";
import { useTask } from "@/lib/hooks/use-tasks";
import type { Agent } from "@/types/agent";

interface TryAgentPanelProps {
  agent: Agent;
}

export function TryAgentPanel({ agent }: TryAgentPanelProps) {
  const [input, setInput] = useState("");
  const [selectedSkill, setSelectedSkill] = useState(
    agent.skills[0]?.id ?? ""
  );
  const [taskId, setTaskId] = useState<string | null>(null);
  const createTask = useCreateTask();
  const { data: task } = useTask(taskId ?? "");

  const isWorking =
    task && ["submitted", "working", "input_required"].includes(task.status);
  const isDone =
    task && ["completed", "failed", "canceled", "rejected"].includes(task.status);

  async function handleSend() {
    if (!input.trim() || !selectedSkill) return;

    try {
      const newTask = await createTask.mutateAsync({
        provider_agent_id: agent.id,
        skill_id: selectedSkill,
        messages: [
          {
            role: "user",
            parts: [{ type: "text", content: input.trim(), data: null, mime_type: null }],
          },
        ],
      });
      setTaskId(newTask.id);
      setInput("");
    } catch {
      // error handled by mutation
    }
  }

  function handleStarterClick(starter: string) {
    setInput(starter);
  }

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
      {!taskId && agent.conversation_starters.length > 0 && (
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

      {/* Message thread + results */}
      {task && (
        <div className="rounded-lg border p-4 space-y-4">
          <TaskMessageThread
            messages={task.messages}
          />
          {isWorking && (
            <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
              <SpinningLogo spinning size="sm" />
              Agent is working...
            </div>
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

      {/* Input */}
      <div className="flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Type a message..."
          disabled={createTask.isPending || !!isWorking}
        />
        <Button
          onClick={handleSend}
          disabled={
            !input.trim() ||
            !selectedSkill ||
            createTask.isPending ||
            !!isWorking
          }
          title={isDone ? "Send another message" : undefined}
          size="icon"
        >
          {createTask.isPending ? (
            <SpinningLogo spinning size="sm" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
