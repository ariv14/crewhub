"use client";

import Link from "next/link";
import { ListTodo, Plus } from "lucide-react";
import { useTasks } from "@/lib/hooks/use-tasks";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { TaskStatusBadge } from "@/components/tasks/task-status-badge";
import { EmptyState } from "@/components/shared/empty-state";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export default function MyTasksPage() {
  const { data, isLoading } = useTasks();
  const tasks = data?.tasks ?? [];

  return (
    <div>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">My Tasks</h1>
          <p className="mt-1 text-muted-foreground">
            Track your delegated tasks
          </p>
        </div>
        <Button asChild>
          <Link href={ROUTES.newTask}>
            <Plus className="mr-2 h-4 w-4" />
            New Task
          </Link>
        </Button>
      </div>

      <div className="mt-6">
        {!isLoading && tasks.length === 0 ? (
          <EmptyState
            icon={ListTodo}
            title="No tasks yet"
            description="Delegate your first task to an agent"
            action={
              <Button asChild>
                <Link href={ROUTES.agents}>Browse Agents</Link>
              </Button>
            }
          />
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task ID</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Skill</TableHead>
                  <TableHead>Credits</TableHead>
                  <TableHead>Payment</TableHead>
                  <TableHead>Created</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {tasks.map((task) => (
                  <TableRow key={task.id}>
                    <TableCell>
                      <a
                        href={ROUTES.taskDetail(task.id)}
                        className="font-mono text-xs hover:text-primary hover:underline"
                      >
                        {task.id.slice(0, 8)}...
                      </a>
                    </TableCell>
                    <TableCell>
                      <TaskStatusBadge status={task.status} />
                    </TableCell>
                    <TableCell className="text-sm">
                      {typeof task.skill_id === "string"
                        ? task.skill_id.slice(0, 20)
                        : "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {formatCredits(task.credits_charged || task.credits_quoted)}
                    </TableCell>
                    <TableCell className="text-sm capitalize">
                      {task.payment_method}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatRelativeTime(task.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </div>
  );
}
