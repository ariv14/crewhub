// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { Settings2 } from "lucide-react";
import { toast } from "sonner";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useUpdateChannel } from "@/lib/hooks/use-channels";
import type { Channel } from "@/types/channel";

export function ChannelEditSheet({ channel }: { channel: Channel }) {
  const [open, setOpen] = useState(false);
  const [dailyLimit, setDailyLimit] = useState(channel.daily_credit_limit ?? 100);
  const [lowBalance, setLowBalance] = useState(channel.low_balance_threshold ?? 20);
  const [pauseOnLimit, setPauseOnLimit] = useState(channel.pause_on_limit ?? true);
  const [botName, setBotName] = useState(channel.bot_name);
  const updateMutation = useUpdateChannel();

  const handleSave = () => {
    updateMutation.mutate(
      {
        id: channel.id,
        data: {
          bot_name: botName,
          daily_credit_limit: dailyLimit || undefined,
          low_balance_threshold: lowBalance,
          pause_on_limit: pauseOnLimit,
        },
      },
      {
        onSuccess: () => {
          toast.success("Channel updated");
          setOpen(false);
        },
        onError: (err) =>
          toast.error(err instanceof Error ? err.message : "Update failed"),
      }
    );
  };

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button size="sm" variant="outline" className="gap-1.5">
          <Settings2 className="h-3.5 w-3.5" />
          Configure
        </Button>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Configure {channel.bot_name}</SheetTitle>
        </SheetHeader>
        <div className="mt-6 space-y-5">
          <div className="space-y-2">
            <Label htmlFor={`bot-name-${channel.id}`}>Bot Display Name</Label>
            <Input
              id={`bot-name-${channel.id}`}
              value={botName}
              onChange={(e) => setBotName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`daily-limit-${channel.id}`}>Daily Credit Limit</Label>
            <Input
              id={`daily-limit-${channel.id}`}
              type="number"
              min={0}
              value={dailyLimit}
              onChange={(e) => setDailyLimit(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">Max credits per day (0 = unlimited)</p>
          </div>
          <div className="space-y-2">
            <Label htmlFor={`low-balance-${channel.id}`}>Low Balance Alert</Label>
            <Input
              id={`low-balance-${channel.id}`}
              type="number"
              min={0}
              value={lowBalance}
              onChange={(e) => setLowBalance(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              Notify when account credits drop below this
            </p>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label htmlFor={`pause-on-limit-${channel.id}`}>Auto-Pause on Limit</Label>
              <p className="text-xs text-muted-foreground">Pause when daily limit reached</p>
            </div>
            <Switch
              id={`pause-on-limit-${channel.id}`}
              checked={pauseOnLimit}
              onCheckedChange={setPauseOnLimit}
            />
          </div>
          <Button
            onClick={handleSave}
            disabled={updateMutation.isPending}
            className="w-full"
          >
            {updateMutation.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
