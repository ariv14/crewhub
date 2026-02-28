"use client";

import { useState } from "react";
import { Loader2, Send } from "lucide-react";
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

  async function handleSend() {
    if (!input.trim() || !selectedSkill) return;

    try {
      const newTask = await createTask.mutateAsync({
        provider_agent_id: agent.id,
        skill_id: selectedSkill,
        messages: [
          {
            role: "user",
            parts: [{ type: "text", content: input.trim() }],
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

      {/* Message thread */}
      {task && (
        <div className="rounded-lg border p-4">
          <TaskMessageThread
            messages={task.messages}
            artifacts={task.artifacts}
          />
          {isWorking && (
            <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Agent is working...
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
          size="icon"
        >
          {createTask.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
