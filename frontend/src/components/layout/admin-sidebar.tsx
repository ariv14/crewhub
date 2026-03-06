"use client";

import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Users,
  ListTodo,
  Receipt,
  ShieldCheck,
  Activity,
  Settings,
  Terminal,
  Telescope,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ROUTES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { useState } from "react";

const NAV_ITEMS = [
  { href: ROUTES.admin, label: "Overview", icon: LayoutDashboard },
  { href: ROUTES.adminAgents, label: "Agents", icon: Bot },
  { href: ROUTES.adminUsers, label: "Users", icon: Users },
  { href: ROUTES.adminTasks, label: "Tasks", icon: ListTodo },
  { href: ROUTES.adminTransactions, label: "Transactions", icon: Receipt },
  { href: "/admin/calls", label: "LLM Calls", icon: Telescope },
  { href: ROUTES.adminGovernance, label: "Governance", icon: ShieldCheck },
  { href: ROUTES.adminHealth, label: "Health", icon: Activity },
  { href: ROUTES.adminMcp, label: "MCP", icon: Terminal },
  { href: ROUTES.adminSettings, label: "Settings", icon: Settings },
];

export function AdminSidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "relative hidden shrink-0 border-r transition-all duration-200 lg:block",
        collapsed ? "w-16" : "w-56"
      )}
    >
      <div className="flex h-14 items-center justify-between border-b px-4">
        {!collapsed && (
          <span className="text-sm font-semibold text-muted-foreground">
            Admin
          </span>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>
      </div>
      <nav className="flex flex-col gap-1 p-2">
        {NAV_ITEMS.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== ROUTES.admin && pathname.startsWith(item.href));
          return (
            <a
              key={item.href}
              href={item.href}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                collapsed && "justify-center px-2",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4 shrink-0" />
              {!collapsed && item.label}
            </a>
          );
        })}
      </nav>
    </aside>
  );
}
