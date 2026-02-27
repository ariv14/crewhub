import { Badge } from "@/components/ui/badge";
import { TASK_STATUS_COLORS } from "@/lib/constants";
import { cn } from "@/lib/utils";
import type { TaskStatus } from "@/types/task";

interface TaskStatusBadgeProps {
  status: TaskStatus;
}

export function TaskStatusBadge({ status }: TaskStatusBadgeProps) {
  return (
    <Badge
      variant="outline"
      className={cn("capitalize", TASK_STATUS_COLORS[status])}
    >
      {status.replace(/_/g, " ")}
    </Badge>
  );
}
