import { Check } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatCredits } from "@/lib/utils";
import type { PricingModel, PricingTier } from "@/types/agent";

interface AgentPricingTableProps {
  pricing: PricingModel;
}

export function AgentPricingTable({ pricing }: AgentPricingTableProps) {
  if (pricing.tiers.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center">
            <p className="text-2xl font-bold">
              {formatCredits(pricing.credits)} credits
            </p>
            <p className="text-sm text-muted-foreground">
              per {pricing.model.replace("per_", "")}
            </p>
            <Badge variant="secondary" className="mt-2">
              {pricing.license_type}
            </Badge>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {pricing.tiers.map((tier) => (
        <TierCard key={tier.name} tier={tier} licenseType={pricing.license_type} />
      ))}
    </div>
  );
}

function TierCard({
  tier,
  licenseType,
}: {
  tier: PricingTier;
  licenseType: string;
}) {
  return (
    <Card className={cn(tier.is_default && "border-primary")}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{tier.name}</CardTitle>
          {tier.is_default && (
            <Badge variant="default" className="text-xs">
              Default
            </Badge>
          )}
        </div>
        <div className="mt-2">
          <span className="text-3xl font-bold">
            {formatCredits(tier.credits_per_unit)}
          </span>
          <span className="text-sm text-muted-foreground">
            {" "}
            credits / {tier.billing_model.replace("per_", "")}
          </span>
        </div>
        {tier.monthly_fee > 0 && (
          <p className="text-sm text-muted-foreground">
            + {formatCredits(tier.monthly_fee)} credits/month
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {tier.features.length > 0 && (
          <ul className="space-y-1.5">
            {tier.features.map((f) => (
              <li key={f} className="flex items-center gap-2 text-sm">
                <Check className="h-3.5 w-3.5 text-green-400" />
                {f.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
        )}
        {tier.quota && (
          <div className="space-y-1 text-xs text-muted-foreground">
            {tier.quota.daily_tasks != null && (
              <p>{tier.quota.daily_tasks} tasks/day</p>
            )}
            {tier.quota.monthly_tasks != null && (
              <p>{tier.quota.monthly_tasks} tasks/month</p>
            )}
            {tier.quota.rate_limit_rpm != null && (
              <p>{tier.quota.rate_limit_rpm} req/min</p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
