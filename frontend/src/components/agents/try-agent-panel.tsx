"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, Loader2, Send } from "lucide-react";
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
import { useCreateTask, useSuggestDelegation } from "@/lib/hooks/use-tasks";
import { useTask } from "@/lib/hooks/use-tasks";
import type { Agent } from "@/types/agent";
import type { SkillSuggestion } from "@/types/task";

interface TryAgentPanelProps {
  agent: Agent;
}

export function TryAgentPanel({ agent }: TryAgentPanelProps) {
  const [input, setInput] = useState("");
  const [selectedSkill, setSelectedSkill] = useState(
    agent.skills[0]?.id ?? ""
  );
  const [taskId, setTaskId] = useState<string | null>(null);
  const [skillHint, setSkillHint] = useState<SkillSuggestion | null>(null);
  const createTask = useCreateTask();
  const suggest = useSuggestDelegation();
  const { data: task } = useTask(taskId ?? "");

  const isWorking =
    task && ["submitted", "working", "input_required"].includes(task.status);

  // Debounced skill hint check
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const checkSkillHint = useCallback(
    (text: string, currentSkillId: string) => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      setSkillHint(null);

      if (text.length < 20 || !currentSkillId) return;

      debounceRef.current = setTimeout(async () => {
        try {
          const result = await suggest.mutateAsync({
            message: text,
            category: agent.category,
            limit: 1,
          });
          if (result.suggestions.length > 0) {
            const top = result.suggestions[0];
            // Only show hint if the best match is different from selected
            if (top.skill.id !== currentSkillId && top.confidence > 0.3) {
              setSkillHint(top);
            }
          }
        } catch {
          // non-critical
        }
      }, 800);
    },
    [suggest, agent.category]
  );

  useEffect(() => {
    if (!taskId) {
      checkSkillHint(input, selectedSkill);
    }
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [input, selectedSkill]); // eslint-disable-line react-hooks/exhaustive-deps

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
      setSkillHint(null);
    } catch {
      // error handled by mutation
    }
  }

  function handleStarterClick(starter: string) {
    setInput(starter);
  }

  function handleSwitchSkill(newSkillId: string) {
    setSelectedSkill(newSkillId);
    setSkillHint(null);
  }

  return (
    <div className="space-y-4">
      {/* Skill selector */}
      {agent.skills.length > 1 && (
        <div className="space-y-1">
          <label className="text-sm font-medium">Skill</label>
          <Select value={selectedSkill} onValueChange={(v) => { setSelectedSkill(v); setSkillHint(null); }}>
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

      {/* Skill mismatch hint */}
      {skillHint && !taskId && (
        <div className="space-y-1">
          {skillHint.agent.id === agent.id ? (
            <button
              type="button"
              onClick={() => handleSwitchSkill(skillHint.skill.id)}
              className="flex w-full items-center gap-2 rounded-md bg-yellow-50 p-2 text-left text-sm text-yellow-700 transition-colors hover:bg-yellow-100 dark:bg-yellow-950 dark:text-yellow-300 dark:hover:bg-yellow-900"
            >
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>
                This might be better handled by{" "}
                <strong>{skillHint.skill.name}</strong>
              </span>
            </button>
          ) : (
            <div className="flex items-center gap-2 rounded-md bg-orange-50 p-2 text-sm text-orange-700 dark:bg-orange-950 dark:text-orange-300">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>
                A different agent might be better for this. Try auto-delegation
                on the{" "}
                <a
                  href="/dashboard/tasks/new"
                  className="underline hover:no-underline"
                >
                  task page
                </a>
                .
              </span>
            </div>
          )}
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
