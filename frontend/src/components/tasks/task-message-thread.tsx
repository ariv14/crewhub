import { cn, formatRelativeTime } from "@/lib/utils";
import type { TaskMessage } from "@/types/task";

interface TaskMessageThreadProps {
  messages: TaskMessage[];
  agentName?: string;
  statusHistory?: { status: string; at: string }[] | null;
}

export function TaskMessageThread({
  messages,
  agentName,
  statusHistory,
}: TaskMessageThreadProps) {
  const createdAt = statusHistory?.find(
    (h) => h.status === "submitted"
  )?.at;

  return (
    <div className="space-y-4">
      {messages.map((msg, i) => {
        const isUser = msg.role === "user";
        const label = isUser ? "You" : agentName || "Agent";
        const timestamp =
          i === 0 && createdAt
            ? createdAt
            : !isUser
              ? statusHistory?.find(
                  (h) =>
                    h.status === "working" || h.status === "completed"
                )?.at
              : null;

        return (
          <div
            key={i}
            className={cn(
              "rounded-lg border p-4",
              isUser ? "ml-8 bg-primary/5" : "mr-8 bg-muted/30"
            )}
          >
            <div className="mb-1 flex items-center justify-between">
              <p className="text-xs font-medium text-muted-foreground">
                {label}
              </p>
              {timestamp && (
                <span className="text-[10px] text-muted-foreground">
                  {formatRelativeTime(timestamp)}
                </span>
              )}
            </div>
            {msg.parts.map((part, j) => (
              <div key={j}>
                {part.type === "text" && part.content && (
                  <p className="whitespace-pre-wrap text-sm">
                    {part.content}
                  </p>
                )}
                {part.type === "data" && part.data && (
                  <pre className="mt-1 overflow-auto rounded bg-muted p-2 text-xs">
                    {JSON.stringify(part.data, null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}
