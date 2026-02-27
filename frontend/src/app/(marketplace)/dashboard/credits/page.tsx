"use client";

import { useState } from "react";
import { useBalance, useTransactions, usePurchaseCredits } from "@/lib/hooks/use-credits";
import { BalanceCard } from "@/components/credits/balance-card";
import { formatCredits, formatRelativeTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

export default function CreditsPage() {
  const { data: balance, isLoading: balanceLoading } = useBalance();
  const { data: txData } = useTransactions({ per_page: 20 });
  const purchase = usePurchaseCredits();
  const [amount, setAmount] = useState("");

  function handlePurchase() {
    const num = Number(amount);
    if (num > 0) {
      purchase.mutate(num, { onSuccess: () => setAmount("") });
    }
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Credits</h1>
        <p className="mt-1 text-muted-foreground">
          Manage your credit balance and view transactions
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {balanceLoading ? (
          <Skeleton className="h-40" />
        ) : balance ? (
          <BalanceCard balance={balance} />
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Purchase Credits</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                type="number"
                min="1"
                placeholder="Amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <Button onClick={handlePurchase} disabled={purchase.isPending}>
                {purchase.isPending ? "Purchasing..." : "Purchase"}
              </Button>
            </div>
            <div className="mt-3 flex gap-2">
              {[100, 500, 1000].map((v) => (
                <Button
                  key={v}
                  variant="outline"
                  size="sm"
                  onClick={() => setAmount(String(v))}
                >
                  {v}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

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
                    <Badge variant="outline" className="capitalize text-xs">
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
