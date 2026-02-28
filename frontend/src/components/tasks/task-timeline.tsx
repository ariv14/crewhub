import { CheckCircle2, Circle, Clock, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface StatusEntry {
  status: string;
  at: string;
}

interface TaskTimelineProps {
  history: StatusEntry[];
}

const STATUS_ICON: Record<string, { icon: typeof Circle; color: string }> = {
  submitted: { icon: Circle, color: "text-blue-500" },
  pending_payment: { icon: Clock, color: "text-amber-500" },
  working: { icon: Clock, color: "text-blue-500" },
  input_required: { icon: Clock, color: "text-yellow-500" },
  completed: { icon: CheckCircle2, color: "text-green-500" },
  failed: { icon: XCircle, color: "text-red-500" },
  canceled: { icon: XCircle, color: "text-muted-foreground" },
  rejected: { icon: XCircle, color: "text-red-500" },
};

export function TaskTimeline({ history }: TaskTimelineProps) {
  if (!history || history.length === 0) return null;

  return (
    <div className="space-y-0">
      {history.map((entry, i) => {
        const config = STATUS_ICON[entry.status] ?? {
          icon: Circle,
          color: "text-muted-foreground",
        };
        const Icon = config.icon;
        const isLast = i === history.length - 1;
        const time = new Date(entry.at);

        return (
          <div key={i} className="flex gap-3">
            <div className="flex flex-col items-center">
              <Icon className={cn("h-4 w-4 shrink-0", config.color)} />
              {!isLast && (
                <div className="my-1 w-px flex-1 bg-border" />
              )}
            </div>
            <div className="pb-4">
              <p className="text-sm font-medium capitalize">
                {entry.status.replace(/_/g, " ")}
              </p>
              <p className="text-xs text-muted-foreground">
                {time.toLocaleTimeString()} &middot;{" "}
                {time.toLocaleDateString()}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
