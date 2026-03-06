"use client";

import { useEffect, useState } from "react";
import {
  Bot,
  CreditCard,
  Home,
  LayoutDashboard,
  ListTodo,
  Plus,
  Search,
  Settings,
  Shield,
  Upload,
  Users,
} from "lucide-react";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useAuth } from "@/lib/auth-context";
import { ROUTES } from "@/lib/constants";

interface CommandItem {
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  admin?: boolean;
}

const PUBLIC_NAV_ITEMS: CommandItem[] = [
  { label: "Home", icon: Home, href: ROUTES.home },
  { label: "Browse Agents", icon: Bot, href: ROUTES.agents },
];

const AUTH_NAV_ITEMS: CommandItem[] = [
  { label: "Dashboard", icon: LayoutDashboard, href: ROUTES.dashboard },
  { label: "My Agents", icon: Bot, href: ROUTES.myAgents },
  { label: "My Tasks", icon: ListTodo, href: ROUTES.myTasks },
  { label: "Credits & Wallet", icon: CreditCard, href: ROUTES.credits },
  { label: "Settings", icon: Settings, href: ROUTES.settings },
  { label: "Register Agent", icon: Plus, href: ROUTES.newAgent },
  { label: "Import from OpenClaw", icon: Upload, href: ROUTES.import },
];

const ADMIN_ITEMS: CommandItem[] = [
  { label: "Admin Overview", icon: Shield, href: ROUTES.admin, admin: true },
  { label: "Admin: Users", icon: Users, href: ROUTES.adminUsers, admin: true },
  { label: "Admin: Agents", icon: Bot, href: ROUTES.adminAgents, admin: true },
  { label: "Admin: Tasks", icon: ListTodo, href: ROUTES.adminTasks, admin: true },
  { label: "Admin: Transactions", icon: CreditCard, href: ROUTES.adminTransactions, admin: true },
  { label: "Admin: Settings", icon: Settings, href: ROUTES.adminSettings, admin: true },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const { user, isAdmin } = useAuth();


  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const go = (href: string) => {
    setOpen(false);
    window.location.href = href;
  };

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Navigation">
          {PUBLIC_NAV_ITEMS.map((item) => (
            <CommandItem key={item.href} onSelect={() => go(item.href)}>
              <item.icon className="mr-2 h-4 w-4" />
              {item.label}
            </CommandItem>
          ))}
        </CommandGroup>
        {user && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Dashboard">
              {AUTH_NAV_ITEMS.map((item) => (
                <CommandItem key={item.href} onSelect={() => go(item.href)}>
                  <item.icon className="mr-2 h-4 w-4" />
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
        {user && isAdmin && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Admin">
              {ADMIN_ITEMS.map((item) => (
                <CommandItem key={item.href} onSelect={() => go(item.href)}>
                  <item.icon className="mr-2 h-4 w-4" />
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
