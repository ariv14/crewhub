import { cn } from "@/lib/utils";
import type { TaskMessage, Artifact } from "@/types/task";

interface TaskMessageThreadProps {
  messages: TaskMessage[];
  artifacts: Artifact[];
}

export function TaskMessageThread({ messages, artifacts }: TaskMessageThreadProps) {
  return (
    <div className="space-y-4">
      {messages.map((msg, i) => (
        <div
          key={i}
          className={cn(
            "rounded-lg border p-4",
            msg.role === "user" ? "ml-8 bg-primary/5" : "mr-8 bg-muted/30"
          )}
        >
          <p className="mb-1 text-xs font-medium text-muted-foreground">
            {msg.role}
          </p>
          {msg.parts.map((part, j) => (
            <div key={j}>
              {part.type === "text" && part.content && (
                <p className="whitespace-pre-wrap text-sm">{part.content}</p>
              )}
              {part.type === "data" && part.data && (
                <pre className="mt-1 overflow-auto rounded bg-muted p-2 text-xs">
                  {JSON.stringify(part.data, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      ))}

      {artifacts.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold">Artifacts</h4>
          {artifacts.map((artifact, i) => (
            <div key={i} className="rounded-lg border p-4">
              {artifact.name && (
                <p className="mb-2 text-sm font-medium">{artifact.name}</p>
              )}
              {artifact.parts.map((part, j) => (
                <div key={j}>
                  {part.type === "text" && part.content && (
                    <p className="whitespace-pre-wrap text-sm">{part.content}</p>
                  )}
                  {part.type === "data" && part.data && (
                    <pre className="overflow-auto rounded bg-muted p-2 text-xs">
                      {JSON.stringify(part.data, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
