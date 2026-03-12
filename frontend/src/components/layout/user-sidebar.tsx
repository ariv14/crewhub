"use client";

import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  ListTodo,
  CreditCard,
  Wallet,
  Settings,
  Upload,
  Users,
  UsersRound,
  GitBranch,
  Clock,
  MessageCircle,
  BookOpen,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ROUTES, DISCORD_URL } from "@/lib/constants";

const NAV_ITEMS = [
  { href: ROUTES.dashboard, label: "Overview", icon: LayoutDashboard },
  { href: ROUTES.myAgents, label: "My Agents", icon: Bot },
  { href: ROUTES.myTasks, label: "My Tasks", icon: ListTodo },
  { href: ROUTES.team, label: "Team", icon: Users },
  { href: ROUTES.myCrews, label: "My Crews", icon: UsersRound },
  { href: ROUTES.myWorkflows, label: "Workflows", icon: GitBranch },
  { href: ROUTES.mySchedules, label: "Schedules", icon: Clock },
  { href: ROUTES.credits, label: "Credits", icon: CreditCard },
  { href: ROUTES.payouts, label: "Payouts", icon: Wallet },
  { href: ROUTES.import, label: "Import", icon: Upload },
  { href: ROUTES.docs, label: "Docs", icon: BookOpen },
  { href: ROUTES.settings, label: "Settings", icon: Settings },
];

export function UserSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-56 shrink-0 border-r lg:flex lg:flex-col">
      <nav className="flex flex-col gap-1 p-4">
        {NAV_ITEMS.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== ROUTES.dashboard &&
              pathname.startsWith(item.href));
          return (
            <a
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </a>
          );
        })}
      </nav>
      <div className="mt-auto border-t p-4">
        <a
          href={DISCORD_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent/50 hover:text-foreground"
        >
          <MessageCircle className="h-4 w-4" />
          Join Community
        </a>
      </div>
    </aside>
  );
}
