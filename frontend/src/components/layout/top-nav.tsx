// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  Bot,
  Clock,
  Compass,
  CreditCard,
  GitBranch,
  LayoutDashboard,
  ListTodo,
  LogOut,
  Map,
  Menu,
  Radio,
  Search,
  Server,
  Settings,
  Shield,
  Sparkles,
  User,
  Wallet,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useHotkeys } from "@/lib/hooks/use-hotkeys";
import { SpinningLogo } from "@/components/shared/spinning-logo";
import { useBalance } from "@/lib/hooks/use-credits";
import { ROUTES } from "@/lib/constants";
import { formatCredits, cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { openCommandPalette } from "@/components/shared/command-palette";
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
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export function TopNav() {
  const { user, loading: authLoading, logout, isAdmin } = useAuth();
  const { data: balance } = useBalance();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  useHotkeys();

  // Synchronous hint: if a token exists in localStorage, user was previously
  // authenticated. Show auth-gated nav items during loading to prevent flash.
  // Guests (no token) never see them — no flash in either direction.
  const hasStoredToken = typeof window !== "undefined" && !!localStorage.getItem("auth_token");
  const showAuthNav = !!user || (authLoading && hasStoredToken);
  const isDashboard = pathname.startsWith("/dashboard");

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/80 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-2 px-4 sm:gap-4 overflow-hidden">
        {/* Mobile hamburger — visible below lg on dashboard, below md on public */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetTrigger asChild className={isDashboard ? "lg:hidden" : "md:hidden"}>
            <Button variant="ghost" size="icon" aria-label="Open menu">
              <Menu className="h-5 w-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64">
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2">
                <SpinningLogo size="sm" />
                CrewHub
              </SheetTitle>
              <SheetDescription className="sr-only">Navigation menu</SheetDescription>
            </SheetHeader>
            <nav className="mt-6 flex flex-col gap-1 overflow-y-auto max-h-[calc(100dvh-8rem)] pb-4">
              {showAuthNav && isDashboard ? (
                <>
                  {/* Dashboard mobile menu — mirrors sidebar exactly */}
                  <span className="px-3 mb-1 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Core</span>
                  {[
                    { href: ROUTES.dashboard, label: "Overview", icon: LayoutDashboard },
                    { href: ROUTES.myAgents, label: "My Agents", icon: Bot },
                    { href: "/agents", label: "Browse Agents", icon: Compass },
                    { href: ROUTES.myTasks, label: "My Tasks", icon: ListTodo },
                  ].map((item) => (
                    <Button key={item.href} variant={pathname === item.href || (item.href !== ROUTES.dashboard && pathname.startsWith(item.href)) ? "secondary" : "ghost"} className="justify-start" asChild>
                      <a href={item.href} onClick={() => setMobileOpen(false)}>
                        <item.icon className="mr-2 h-4 w-4" />
                        {item.label}
                      </a>
                    </Button>
                  ))}
                  <div className="my-2 border-t" />
                  <span className="px-3 mb-1 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Orchestration</span>
                  {[
                    { href: ROUTES.myWorkflows, label: "Workflows", icon: GitBranch },
                    { href: ROUTES.mySchedules, label: "Schedules", icon: Clock },
                    { href: "/dashboard/channels", label: "Channels", icon: Radio },
                    { href: "/dashboard/builder", label: "Build Agent", icon: Sparkles },
                    { href: "/dashboard/mcp", label: "MCP Servers", icon: Server },
                  ].map((item) => (
                    <Button key={item.href} variant={pathname === item.href || pathname.startsWith(item.href) ? "secondary" : "ghost"} className="justify-start" asChild>
                      <a href={item.href} onClick={() => setMobileOpen(false)}>
                        <item.icon className="mr-2 h-4 w-4" />
                        {item.label}
                      </a>
                    </Button>
                  ))}
                  <div className="my-2 border-t" />
                  <span className="px-3 mb-1 text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">Account</span>
                  {[
                    { href: ROUTES.credits, label: "Credits", icon: CreditCard },
                    { href: ROUTES.payouts, label: "Payouts", icon: Wallet },
                    { href: ROUTES.settings, label: "Settings", icon: Settings },
                  ].map((item) => (
                    <Button key={item.href} variant={pathname === item.href || pathname.startsWith(item.href) ? "secondary" : "ghost"} className="justify-start" asChild>
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
                  <div className="my-2 border-t" />
                  {[
                    { href: ROUTES.docs, label: "Docs", icon: BookOpen },
                    { href: "/guide", label: "Guide", icon: Map },
                    { href: ROUTES.pricing, label: "Pricing", icon: CreditCard },
                    { href: "/explore", label: "Explore", icon: Compass },
                  ].map((item) => (
                    <Button key={item.href} variant="ghost" className="justify-start" asChild>
                      <a href={item.href} onClick={() => setMobileOpen(false)}>
                        <item.icon className="mr-2 h-4 w-4" />
                        {item.label}
                      </a>
                    </Button>
                  ))}
                </>
              ) : (
                <>
                  {/* Public pages mobile menu */}
                  {showAuthNav && (
                    <>
                      {[
                        { href: ROUTES.dashboard, label: "Dashboard", icon: LayoutDashboard },
                        { href: ROUTES.myAgents, label: "My Agents", icon: Bot },
                        { href: ROUTES.myTasks, label: "My Tasks", icon: ListTodo },
                      ].map((item) => (
                        <Button key={item.href} variant={pathname === item.href || (item.href !== ROUTES.dashboard && pathname.startsWith(item.href)) ? "secondary" : "ghost"} className="justify-start" asChild>
                          <a href={item.href} onClick={() => setMobileOpen(false)}>
                            <item.icon className="mr-2 h-4 w-4" />
                            {item.label}
                          </a>
                        </Button>
                      ))}
                      <div className="my-2 border-t" />
                    </>
                  )}
                  {[
                    { href: "/agents", label: "Browse Agents", icon: Search },
                    { href: ROUTES.docs, label: "Docs", icon: BookOpen },
                    { href: ROUTES.pricing, label: "Pricing", icon: CreditCard },
                    { href: "/guide", label: "Guide", icon: BookOpen },
                    { href: "/explore", label: "Explore", icon: LayoutDashboard },
                  ].map((item) => (
                    <Button key={item.href} variant={pathname === item.href ? "secondary" : "ghost"} className="justify-start" asChild>
                      <a href={item.href} onClick={() => setMobileOpen(false)}>
                        <item.icon className="mr-2 h-4 w-4" />
                        {item.label}
                      </a>
                    </Button>
                  ))}
                  {!user && (
                    <Button variant="ghost" className="justify-start text-primary" asChild>
                      <a href={ROUTES.register} onClick={() => setMobileOpen(false)}>
                        <Sparkles className="mr-2 h-4 w-4" />
                        Get Started Free
                      </a>
                    </Button>
                  )}
                </>
              )}
            </nav>
          </SheetContent>
        </Sheet>

        <a href={user ? ROUTES.dashboard : ROUTES.home} className="flex min-w-0 flex-shrink-0 items-center gap-2 font-bold text-lg">
          <SpinningLogo size="md" />
          <span className={user ? "hidden sm:inline" : ""}>CrewHub</span>
        </a>

        {/* Desktop nav — only on public pages; hidden entirely on dashboard (sidebar handles it) */}
        {!isDashboard && (
          <nav className="hidden items-center gap-1 md:flex">
            {showAuthNav && (
              <Button variant="ghost" size="sm" asChild className={pathname === "/dashboard" ? "bg-accent" : ""}>
                <a href={ROUTES.dashboard}>Dashboard</a>
              </Button>
            )}
            <Button variant="ghost" size="sm" asChild className={pathname.startsWith("/agents") ? "bg-accent" : ""}>
              <a href="/agents">Agents</a>
            </Button>
            <Button variant="ghost" size="sm" asChild className={pathname === "/docs" ? "bg-accent" : ""}>
              <a href={ROUTES.docs}>Docs</a>
            </Button>
            <Button variant="ghost" size="sm" asChild className={pathname === "/pricing" ? "bg-accent" : ""}>
              <a href={ROUTES.pricing}>Pricing</a>
            </Button>
            <Button variant="ghost" size="sm" asChild className={pathname === "/guide" ? "bg-accent" : ""}>
              <a href={ROUTES.guide}>Guide</a>
            </Button>
          </nav>
        )}

        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="icon" className="hidden md:flex" onClick={openCommandPalette} aria-label="Search">
            <Search className="h-4 w-4" />
          </Button>

          {user && balance && (
            <a href={ROUTES.credits} aria-label={`Credits: ${formatCredits(balance.available)}`}>
              <Badge
                variant={balance.available < 10 ? "destructive" : "secondary"}
                className={cn(
                  "cursor-pointer gap-1 px-1.5 py-0.5 text-[11px] sm:px-2.5 sm:py-1 sm:text-xs",
                  balance.available < 50 && balance.available >= 10 && "border-amber-500/50 text-amber-500",
                  balance.available < 10 && "animate-pulse"
                )}
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
                <DropdownMenuItem onClick={async () => { await logout(); window.location.href = "/"; }}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : authLoading ? null : (
            <>
              <a href={`${ROUTES.login}?redirect=${encodeURIComponent(pathname)}`} className="text-sm text-muted-foreground hover:text-foreground">
                Sign In
              </a>
              <Button size="sm" className="hidden sm:inline-flex" asChild>
                <a href={ROUTES.register}>Get Started Free</a>
              </Button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
