"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Bot,
  CreditCard,
  LayoutDashboard,
  ListTodo,
  LogOut,
  Menu,
  Search,
  Settings,
  Shield,
  Upload,
  User,
  Users,
  UsersRound,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import { useBalance } from "@/lib/hooks/use-credits";
import { ROUTES } from "@/lib/constants";
import { formatCredits } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export function TopNav() {
  const { user, loading: authLoading, logout, isAdmin } = useAuth();
  const { data: balance } = useBalance();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-4 px-4">
        {/* Mobile hamburger */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild className="md:hidden">
            <Button variant="ghost" size="icon">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64">
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                <SpinningLogo size="sm" />
                CrewHub
              </SheetTitle>
            </SheetHeader>
            <nav className="mt-6 flex flex-col gap-1">
              {user && (
                <>
                  {[
                    { href: ROUTES.dashboard, label: "Overview", icon: LayoutDashboard },
                    { href: ROUTES.myAgents, label: "My Agents", icon: Bot },
                    { href: ROUTES.myTasks, label: "My Tasks", icon: ListTodo },
                    { href: ROUTES.team, label: "Team", icon: Users },
                    { href: ROUTES.myCrews, label: "My Crews", icon: UsersRound },
                    { href: ROUTES.credits, label: "Credits", icon: CreditCard },
                    { href: ROUTES.import, label: "Import", icon: Upload },
                    { href: ROUTES.settings, label: "Settings", icon: Settings },
                  ].map((item) => (
                    <Button key={item.href} variant={pathname === item.href || (item.href !== ROUTES.dashboard && pathname.startsWith(item.href)) ? "secondary" : "ghost"} className="justify-start" asChild>
                      <a href={item.href} onClick={() => setMobileOpen(false)}>
                        <item.icon className="mr-2 h-4 w-4" />
                        {item.label}
                      </a>
                    </Button>
                  ))}
                  {isAdmin && (
                    <Button variant="ghost" className="justify-start" asChild>
                      <a href={ROUTES.admin} onClick={() => setMobileOpen(false)}>
                        <Shield className="mr-2 h-4 w-4" />
                        Admin
                      </a>
                    </Button>
                  )}
                </>
              )}
              <div className="my-2 border-t" />
              <Button variant="ghost" className="justify-start" asChild>
                <a href="/agents" onClick={() => setMobileOpen(false)}>
                  <Search className="mr-2 h-4 w-4" />
                  Browse Agents
                </a>
              </Button>
              <Button variant="ghost" className="justify-start" asChild>
                <a href={ROUTES.docs} onClick={() => setMobileOpen(false)}>
                  <BookOpen className="mr-2 h-4 w-4" />
                  Docs
                </a>
              </Button>
              <Button variant="ghost" className="justify-start" asChild>
                <a href={ROUTES.pricing} onClick={() => setMobileOpen(false)}>
                  <CreditCard className="mr-2 h-4 w-4" />
                  Pricing
                </a>
              </Button>
            </nav>
          </SheetContent>
        </Sheet>

        <a href={user ? ROUTES.dashboard : ROUTES.home} className="flex items-center gap-2 font-bold">
          <SpinningLogo size="sm" />
          <span>CrewHub</span>
        </a>

        <nav className="hidden items-center gap-1 md:flex">
          {user && (
            <>
              <Button variant="ghost" size="sm" asChild className={pathname === "/dashboard" ? "bg-accent" : ""}>
                <a href={ROUTES.dashboard}>Dashboard</a>
              </Button>
              <Button variant="ghost" size="sm" asChild className={pathname.startsWith("/agents") ? "bg-accent" : ""}>
                <a href="/agents">Agents</a>
              </Button>
              <Button variant="ghost" size="sm" asChild className={pathname.startsWith("/dashboard/tasks") ? "bg-accent" : ""}>
                <a href={ROUTES.myTasks}>Tasks</a>
              </Button>
            </>
          )}
          <Button variant="ghost" size="sm" asChild className={pathname === "/docs" ? "bg-accent" : ""}>
            <a href={ROUTES.docs}>Docs</a>
          </Button>
          <Button variant="ghost" size="sm" asChild className={pathname === "/pricing" ? "bg-accent" : ""}>
            <a href={ROUTES.pricing}>Pricing</a>
          </Button>
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="icon" className="hidden md:flex">
            <Search className="h-4 w-4" />
          </Button>

          {user && balance && (
            <a href={ROUTES.credits}>
              <Badge
                variant="secondary"
                className="cursor-pointer gap-1 px-2.5 py-1"
              >
                <CreditCard className="h-3 w-3" />
                {formatCredits(balance.available)}
              </Badge>
            </a>
          )}

          <ThemeToggle />

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="relative h-8 w-8 rounded-full"
                >
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="text-xs">
                      {user.name.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-48">
                <div className="px-2 py-1.5">
                  <p className="text-sm font-medium">{user.name}</p>
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                </div>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <a href={ROUTES.dashboard}>
                    <User className="mr-2 h-4 w-4" />
                    Dashboard
                  </a>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <a href={ROUTES.settings}>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </a>
                </DropdownMenuItem>
                {isAdmin && (
                  <DropdownMenuItem asChild>
                    <a href={ROUTES.admin}>
                      <Shield className="mr-2 h-4 w-4" />
                      Admin
                    </a>
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => logout()}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : authLoading ? null : (
            <Button size="sm" asChild>
              <a href={ROUTES.login}>Sign In</a>
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
