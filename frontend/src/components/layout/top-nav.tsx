"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  CreditCard,
  LogOut,
  Menu,
  Search,
  Settings,
  User,
  Shield,
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
  const { user, logout, isAdmin } = useAuth();
  const { data: balance } = useBalance();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const mobileGo = (href: string) => {
    setMobileOpen(false);
    router.push(href);
  };

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
                  <Button variant="ghost" className="justify-start" onClick={() => mobileGo(ROUTES.dashboard)}>
                    Dashboard
                  </Button>
                  <Button variant="ghost" className="justify-start" onClick={() => mobileGo(ROUTES.myTasks)}>
                    My Tasks
                  </Button>
                  <Button variant="ghost" className="justify-start" onClick={() => mobileGo(ROUTES.credits)}>
                    Credits
                  </Button>
                  <Button variant="ghost" className="justify-start" onClick={() => mobileGo(ROUTES.settings)}>
                    Settings
                  </Button>
                  {isAdmin && (
                    <Button variant="ghost" className="justify-start" onClick={() => mobileGo(ROUTES.admin)}>
                      <Shield className="mr-2 h-4 w-4" />
                      Admin
                    </Button>
                  )}
                </>
              )}
            </nav>
          </SheetContent>
        </Sheet>

        <Link href={user ? ROUTES.dashboard : ROUTES.home} className="flex items-center gap-2 font-bold">
          <SpinningLogo size="sm" />
          <span>CrewHub</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {user && (
            <>
              <Button variant="ghost" size="sm" asChild className={pathname === "/dashboard" ? "bg-accent" : ""}>
                <Link href={ROUTES.dashboard}>Dashboard</Link>
              </Button>
              <Button variant="ghost" size="sm" asChild className={pathname.startsWith("/agents") ? "bg-accent" : ""}>
                <Link href="/agents">Agents</Link>
              </Button>
              <Button variant="ghost" size="sm" asChild className={pathname.startsWith("/dashboard/tasks") ? "bg-accent" : ""}>
                <Link href={ROUTES.myTasks}>Tasks</Link>
              </Button>
            </>
          )}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="icon" className="hidden md:flex">
            <Search className="h-4 w-4" />
          </Button>

          {user && balance && (
            <Link href={ROUTES.credits}>
              <Badge
                variant="secondary"
                className="cursor-pointer gap-1 px-2.5 py-1"
              >
                <CreditCard className="h-3 w-3" />
                {formatCredits(balance.available)}
              </Badge>
            </Link>
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
                <DropdownMenuItem onClick={() => router.push(ROUTES.dashboard)}>
                  <User className="mr-2 h-4 w-4" />
                  Dashboard
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => router.push(ROUTES.settings)}>
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </DropdownMenuItem>
                {isAdmin && (
                  <DropdownMenuItem onClick={() => router.push(ROUTES.admin)}>
                    <Shield className="mr-2 h-4 w-4" />
                    Admin
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => logout()}>
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Button size="sm" asChild>
              <Link href={ROUTES.login}>Sign In</Link>
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
