// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCredits } from "@/lib/utils";
import type { Skill } from "@/types/agent";

interface AgentSkillsListProps {
  skills: Skill[];
}

export function AgentSkillsList({ skills }: AgentSkillsListProps) {
  if (skills.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No skills registered for this agent.
      </p>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {skills.map((skill) => (
        <Card key={skill.id}>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">{skill.name}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {skill.description}
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-1.5">
              <Badge variant="secondary" className="text-xs">
                {skill.skill_key}
              </Badge>
              {skill.input_modes.map((m) => (
                <Badge key={m} variant="outline" className="text-xs">
                  in: {m}
                </Badge>
              ))}
              {skill.output_modes.map((m) => (
                <Badge key={m} variant="outline" className="text-xs">
                  out: {m}
                </Badge>
              ))}
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>~{formatCredits(skill.avg_credits)} credits</span>
              <span>~{skill.avg_latency_ms}ms</span>
            </div>
            {skill.examples.length > 0 && (
              <details className="text-xs">
                <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                  {skill.examples.length} example(s)
                </summary>
                <div className="mt-2 space-y-2">
                  {skill.examples.map((ex, i) => (
                    <div key={i} className="rounded border bg-muted/30 p-2">
                      {ex.description && (
                        <p className="mb-1 font-medium">{ex.description}</p>
                      )}
                      <p>
                        <span className="text-muted-foreground">Input: </span>
                        {ex.input}
                      </p>
                      <p>
                        <span className="text-muted-foreground">Output: </span>
                        {ex.output}
                      </p>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
