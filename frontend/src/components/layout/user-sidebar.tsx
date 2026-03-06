"use client";

import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  ListTodo,
  CreditCard,
  Settings,
  Upload,
  Users,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";

const NAV_ITEMS = [
  { href: ROUTES.dashboard, label: "Overview", icon: LayoutDashboard },
  { href: ROUTES.myAgents, label: "My Agents", icon: Bot },
  { href: ROUTES.myTasks, label: "My Tasks", icon: ListTodo },
  { href: ROUTES.team, label: "Team", icon: Users },
  { href: ROUTES.credits, label: "Credits", icon: CreditCard },
  { href: ROUTES.import, label: "Import", icon: Upload },
  { href: ROUTES.settings, label: "Settings", icon: Settings },
];

export function UserSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-56 shrink-0 border-r lg:block">
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
    </aside>
  );
}
