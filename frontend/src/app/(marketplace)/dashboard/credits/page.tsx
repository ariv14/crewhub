"use client";

import { useState } from "react";
import { useBalance, useTransactions, useUsage, useSpendByAgent } from "@/lib/hooks/use-credits";
import { createCreditsCheckout } from "@/lib/api/billing";
import { BalanceCard } from "@/components/credits/balance-card";
import { SpendBreakdown } from "@/components/credits/spend-breakdown";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { Coins, Zap, Sparkles, Crown, TrendingUp, ArrowDownLeft, ArrowUpRight, Wallet } from "lucide-react";
import Link from "next/link";
import { ROUTES } from "@/lib/constants";

const CREDIT_PACKS = [
  { credits: 500, priceCents: 500, label: "Starter", savings: null, icon: Coins },
  { credits: 2000, priceCents: 1800, label: "Builder", savings: "10% off", icon: Zap },
  { credits: 5000, priceCents: 4000, label: "Pro", savings: "20% off", icon: Sparkles, popular: true },
  { credits: 10000, priceCents: 7000, label: "Enterprise", savings: "30% off", icon: Crown },
] as const;

export default function CreditsPage() {
  const { data: balance, isLoading: balanceLoading } = useBalance();
  const { data: txData } = useTransactions({ per_page: 20 });
  const { data: usage } = useUsage("30d");
  const { data: spendData } = useSpendByAgent("30d");
  const [purchasing, setPurchasing] = useState<number | null>(null);

  async function handlePurchase(credits: number) {
    setPurchasing(credits);
    try {
      const { checkout_url } = await createCreditsCheckout(credits);
      window.location.href = checkout_url;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to start checkout");
      setPurchasing(null);
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Credits</h1>
        <p className="mt-1 text-muted-foreground">
          Purchase credits to run AI agent tasks. 1 credit = $0.01
        </p>
      </div>

      {balanceLoading ? (
        <Skeleton className="h-40" />
      ) : balance ? (
        <BalanceCard balance={balance} />
      ) : null}

      {/* Earnings & Spending Summary */}
      {usage && (usage.total_earned > 0 || usage.total_spent > 0) && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="flex items-center gap-3 pt-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                <ArrowDownLeft className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Earned (30d)</p>
                <p className="text-xl font-bold text-green-600">
                  +{formatCredits(usage.total_earned)}
                </p>
                <Link
                  href={ROUTES.payouts}
                  className="mt-1 inline-flex items-center gap-1 text-xs text-primary hover:underline"
                >
                  <Wallet className="h-3 w-3" />
                  Withdraw
                </Link>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 pt-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10">
                <ArrowUpRight className="h-5 w-5 text-red-500" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Spent (30d)</p>
                <p className="text-xl font-bold">
                  {formatCredits(usage.total_spent)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="flex items-center gap-3 pt-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <TrendingUp className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Tasks (30d)</p>
                <p className="text-xl font-bold">
                  {usage.tasks_created + usage.tasks_received}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Spend Breakdown */}
      {spendData && spendData.breakdown.length > 0 && (
        <SpendBreakdown
          breakdown={spendData.breakdown}
          period={spendData.period}
        />
      )}

      {/* Credit Packs */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Buy Credits</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CREDIT_PACKS.map((pack) => (
            <Card
              key={pack.credits}
              className={`relative transition-all hover:shadow-md ${
                "popular" in pack && pack.popular
                  ? "border-primary shadow-sm"
                  : ""
              }`}
            >
              {"popular" in pack && pack.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-primary text-primary-foreground">
                    Most Popular
                  </Badge>
                </div>
              )}
              <CardHeader className="pb-3 text-center">
                <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <pack.icon className="h-5 w-5 text-primary" />
                </div>
                <CardTitle className="text-base">{pack.label}</CardTitle>
              </CardHeader>
              <CardContent className="text-center">
                <div className="text-3xl font-bold">
                  {pack.credits.toLocaleString()}
                </div>
                <div className="mt-1 text-sm text-muted-foreground">credits</div>
                <div className="mt-3 flex items-center justify-center gap-2">
                  <span className="text-xl font-semibold">
                    ${(pack.priceCents / 100).toFixed(0)}
                  </span>
                  {pack.savings && (
                    <Badge variant="secondary" className="text-xs text-green-600">
                      {pack.savings}
                    </Badge>
                  )}
                </div>
                <div className="mt-1 text-xs text-muted-foreground">
                  ${(pack.priceCents / pack.credits / 100).toFixed(4)}/credit
                </div>
                <Button
                  className="mt-4 w-full"
                  variant={"popular" in pack && pack.popular ? "default" : "outline"}
                  onClick={() => handlePurchase(pack.credits)}
                  disabled={purchasing !== null}
                >
                  {purchasing === pack.credits ? "Redirecting..." : "Buy Now"}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Transaction History */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Transaction History</h2>
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Type</TableHead>
                <TableHead>Amount</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(txData?.transactions ?? []).map((tx) => (
                <TableRow key={tx.id}>
                  <TableCell>
                    <Badge variant="outline" className="text-xs capitalize">
                      {tx.type.replace(/_/g, " ")}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-sm">
                    {tx.type === "purchase" || tx.type === "refund" || tx.type === "bonus"
                      ? "+"
                      : "-"}
                    {formatCredits(tx.amount)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {tx.description}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatRelativeTime(tx.created_at)}
                  </TableCell>
                </TableRow>
              ))}
              {(!txData || txData.transactions.length === 0) && (
                <TableRow>
                  <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                    No transactions yet
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
