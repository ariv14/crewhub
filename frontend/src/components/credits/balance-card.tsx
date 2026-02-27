"use client";

import { CreditCard, Wallet } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { formatCredits } from "@/lib/utils";
import type { Balance } from "@/types/credits";

interface BalanceCardProps {
  balance: Balance;
}

export function BalanceCard({ balance }: BalanceCardProps) {
  return (
    <Card className="relative overflow-hidden">
      <CardContent className="p-6">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Wallet className="h-4 w-4" />
          Available Balance
        </div>
        <p className="mt-2 text-4xl font-bold">
          {formatCredits(balance.available)}
          <span className="ml-2 text-sm font-normal text-muted-foreground">
            credits
          </span>
        </p>
        <div className="mt-4 flex gap-6 text-sm text-muted-foreground">
          <div>
            <p>Total</p>
            <p className="font-medium text-foreground">
              {formatCredits(balance.balance)}
            </p>
          </div>
          <div>
            <p>Reserved</p>
            <p className="font-medium text-foreground">
              {formatCredits(balance.reserved)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
