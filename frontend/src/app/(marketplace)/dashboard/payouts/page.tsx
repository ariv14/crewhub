// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import {
  useConnectStatus,
  useWithdrawableBalance,
  usePayoutHistory,
  useRequestPayout,
  useConnectOnboard,
  usePayoutEstimate,
} from "@/lib/hooks/use-payouts";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
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
import {
  Wallet,
  ExternalLink,
  Clock,
  ArrowDownToLine,
  DollarSign,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";

const STATUS_BADGES: Record<string, { variant: "default" | "secondary" | "destructive" | "outline"; icon: typeof CheckCircle2 }> = {
  pending: { variant: "outline", icon: Clock },
  processing: { variant: "secondary", icon: Loader2 },
  completed: { variant: "default", icon: CheckCircle2 },
  failed: { variant: "destructive", icon: XCircle },
  cancelled: { variant: "outline", icon: XCircle },
};

export default function PayoutsPage() {
  const { data: connectStatus, isLoading: connectLoading } = useConnectStatus();
  const { data: balance, isLoading: balanceLoading } = useWithdrawableBalance();
  const { data: history } = usePayoutHistory();
  const requestPayout = useRequestPayout();
  const connectOnboard = useConnectOnboard();

  const searchParams = useSearchParams();
  const [showWithdraw, setShowWithdraw] = useState(false);
  const [withdrawAmount, setWithdrawAmount] = useState("");

  // Handle Stripe Connect return URL
  useEffect(() => {
    const connectParam = searchParams.get("connect");
    if (connectParam === "success") {
      toast.success("Stripe Connect setup complete! Your account status is being verified.");
    } else if (connectParam === "refresh") {
      toast.info("Onboarding session expired. Please try again.");
    }
  }, [searchParams]);

  const parsedAmount = parseFloat(withdrawAmount) || 0;
  const { data: estimate } = usePayoutEstimate(parsedAmount);

  const isOnboarded = connectStatus?.connected && connectStatus?.onboarded;
  const canWithdraw =
    isOnboarded &&
    balance &&
    balance.withdrawable_credits >= balance.minimum_payout_credits;

  async function handleConnect() {
    try {
      const { onboarding_url } = await connectOnboard.mutateAsync();
      window.location.href = onboarding_url;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to start onboarding";
      if (msg.includes("not yet enabled") || msg.includes("signed up for Connect")) {
        toast.error("Stripe Connect is not yet available. The platform is still setting up payouts — please check back soon.");
      } else {
        toast.error(msg);
      }
    }
  }

  async function handleWithdraw() {
    if (parsedAmount < (balance?.minimum_payout_credits ?? 2500)) {
      toast.error(`Minimum withdrawal is ${formatCredits(balance?.minimum_payout_credits ?? 2500)} credits`);
      return;
    }
    try {
      await requestPayout.mutateAsync(parsedAmount);
      toast.success("Payout requested! Funds will arrive in 1-3 business days.");
      setShowWithdraw(false);
      setWithdrawAmount("");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Payout failed");
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Payouts</h1>
        <p className="mt-1 text-muted-foreground">
          Withdraw your earned credits as real USD to your bank account via Stripe.
        </p>
      </div>

      {/* Connect Card (if not onboarded) */}
      {connectLoading ? (
        <Skeleton className="h-40" />
      ) : !isOnboarded ? (
        <Card className="border-dashed">
          <CardHeader>
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Wallet className="h-5 w-5 text-primary" />
              </div>
              <div>
                <CardTitle>Connect Your Bank Account</CardTitle>
                <CardDescription>
                  Set up Stripe Connect to withdraw your agent earnings as real USD.
                  Stripe handles all identity verification and tax reporting.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Button
              onClick={handleConnect}
              disabled={connectOnboard.isPending}
            >
              {connectOnboard.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Setting up...
                </>
              ) : (
                <>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Connect with Stripe
                </>
              )}
            </Button>
            {connectStatus?.connected && !connectStatus.onboarded && (
              <p className="mt-3 text-sm text-amber-500">
                <AlertCircle className="mr-1 inline h-4 w-4" />
                Onboarding incomplete — click above to finish setup.
              </p>
            )}
          </CardContent>
        </Card>
      ) : null}

      {/* Balance Card (if onboarded) */}
      {isOnboarded && (
        <>
          {balanceLoading ? (
            <Skeleton className="h-48" />
          ) : balance ? (
            <div className="grid gap-4 sm:grid-cols-3">
              <Card>
                <CardContent className="flex items-center gap-3 pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                    <DollarSign className="h-5 w-5 text-green-500" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Withdrawable</p>
                    <p className="text-xl font-bold text-green-600">
                      {formatCredits(balance.withdrawable_credits)} credits
                    </p>
                    <p className="text-sm text-muted-foreground">
                      ${(balance.withdrawable_usd_cents / 100).toFixed(2)} USD
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="flex items-center gap-3 pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/10">
                    <Clock className="h-5 w-5 text-amber-500" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Pending Clearance</p>
                    <p className="text-xl font-bold">
                      {formatCredits(balance.pending_clearance_credits)} credits
                    </p>
                    <p className="text-xs text-muted-foreground">7-day hold after task completion</p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="flex items-center gap-3 pt-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <ArrowDownToLine className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Paid Out</p>
                    <p className="text-xl font-bold">
                      {formatCredits(balance.total_paid_out_credits)} credits
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : null}

          <Button
            size="lg"
            onClick={() => {
              setWithdrawAmount(
                String(Math.floor(balance?.withdrawable_credits ?? 0))
              );
              setShowWithdraw(true);
            }}
            disabled={!canWithdraw}
          >
            <Wallet className="mr-2 h-4 w-4" />
            {canWithdraw
              ? "Withdraw Earnings"
              : `Min ${formatCredits(balance?.minimum_payout_credits ?? 2500)} credits to withdraw`}
          </Button>
        </>
      )}

      {/* Withdrawal Dialog */}
      <Dialog open={showWithdraw} onOpenChange={setShowWithdraw}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Withdraw Credits</DialogTitle>
            <DialogDescription>
              Credits will be converted to USD and transferred to your connected bank account.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div>
              <label className="text-sm font-medium">Amount (credits)</label>
              <Input
                type="number"
                min={balance?.minimum_payout_credits ?? 2500}
                max={balance?.withdrawable_credits ?? 0}
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
                placeholder="2500"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Available: {formatCredits(balance?.withdrawable_credits ?? 0)} credits
                {" · "}Min: {formatCredits(balance?.minimum_payout_credits ?? 2500)}
              </p>
            </div>

            {estimate && parsedAmount >= (balance?.minimum_payout_credits ?? 2500) && (
              <div className="rounded-lg border p-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Gross amount</span>
                  <span className="font-mono">${(estimate.gross_usd_cents / 100).toFixed(2)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Stripe fee (0.25% + $0.25)</span>
                  <span className="font-mono text-red-500">
                    -${(estimate.stripe_fee_cents / 100).toFixed(2)}
                  </span>
                </div>
                <div className="border-t pt-2 flex justify-between font-semibold">
                  <span>You receive</span>
                  <span className="text-green-600">
                    ${(estimate.net_usd_cents / 100).toFixed(2)}
                  </span>
                </div>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWithdraw(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleWithdraw}
              disabled={
                requestPayout.isPending ||
                parsedAmount < (balance?.minimum_payout_credits ?? 2500) ||
                parsedAmount > (balance?.withdrawable_credits ?? 0)
              }
            >
              {requestPayout.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                "Confirm Withdrawal"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Payout History */}
      {isOnboarded && (
        <div>
          <h2 className="mb-4 text-lg font-semibold">Payout History</h2>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Credits</TableHead>
                  <TableHead>Amount (USD)</TableHead>
                  <TableHead>Fee</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(history?.payouts ?? []).map((payout) => {
                  const badge = STATUS_BADGES[payout.status] ?? STATUS_BADGES.pending;
                  const Icon = badge.icon;
                  return (
                    <TableRow key={payout.id}>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatRelativeTime(payout.requested_at)}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {formatCredits(payout.amount_credits)}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        ${(payout.amount_usd_cents / 100).toFixed(2)}
                      </TableCell>
                      <TableCell className="font-mono text-sm text-muted-foreground">
                        ${(payout.stripe_fee_cents / 100).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={badge.variant} className="gap-1 text-xs capitalize">
                          <Icon className="h-3 w-3" />
                          {payout.status}
                        </Badge>
                        {payout.failure_reason && (
                          <p className="mt-1 text-xs text-red-500">{payout.failure_reason}</p>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
                {(!history || history.payouts.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                      No payouts yet
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}
