// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { MessageSquarePlus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { trackEvent } from "@/lib/telemetry";
import { cn } from "@/lib/utils";

const DISCORD_WEBHOOK =
  "https://discord.com/api/webhooks/1480617514512679075/MTGOHMdUipmCU08k1rGO1Qhp29P-EF918Sowi_Xp1wXr5Us-hMWODGuIkTpKNbiVVe2S";

const CATEGORIES = [
  { value: "bug", label: "Bug", emoji: "🐛" },
  { value: "feature", label: "Feature", emoji: "💡" },
  { value: "general", label: "General", emoji: "💬" },
] as const;

type Category = (typeof CATEGORIES)[number]["value"];

export function FeedbackWidget() {
  const [open, setOpen] = useState(false);
  const [category, setCategory] = useState<Category>("general");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit() {
    if (!message.trim()) return;
    setSubmitting(true);
    try {
      const text = message.trim();
      trackEvent("user_feedback", {
        category,
        message: text,
        url: window.location.pathname,
      });
      // Send directly to Discord webhook
      await fetch(DISCORD_WEBHOOK, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          embeds: [{
            title: `${category === "bug" ? "Bug Report" : category === "feature" ? "Feature Request" : "Feedback"}`,
            description: text,
            color: category === "bug" ? 0xEF4444 : category === "feature" ? 0x3B82F6 : 0x7C3AED,
            fields: [
              { name: "Page", value: window.location.pathname, inline: true },
            ],
            timestamp: new Date().toISOString(),
          }],
        }),
      }).catch(() => {});
      toast.success("Thanks for your feedback!");
      setMessage("");
      setOpen(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      {/* Floating trigger button */}
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          "fixed bottom-6 right-6 z-50 flex h-12 w-12 items-center justify-center",
          "rounded-full bg-primary text-primary-foreground shadow-lg",
          "transition-transform hover:scale-110 active:scale-95",
          open && "rotate-45",
        )}
        aria-label="Send feedback"
      >
        {open ? <X className="h-5 w-5" /> : <MessageSquarePlus className="h-5 w-5" />}
      </button>

      {/* Feedback panel */}
      {open && (
        <div className="fixed bottom-20 right-6 z-50 w-80 rounded-xl border bg-card p-4 shadow-xl">
          <h3 className="font-semibold text-sm mb-3">Send Feedback</h3>

          {/* Category selector */}
          <div className="flex gap-2 mb-3">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.value}
                onClick={() => setCategory(cat.value)}
                className={cn(
                  "flex-1 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors",
                  category === cat.value
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border text-muted-foreground hover:bg-accent",
                )}
              >
                {cat.emoji} {cat.label}
              </button>
            ))}
          </div>

          {/* Message */}
          <Textarea
            placeholder={
              category === "bug"
                ? "What went wrong?"
                : category === "feature"
                  ? "What would you like to see?"
                  : "What's on your mind?"
            }
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            rows={3}
            className="mb-3 text-sm resize-none"
          />

          <Button
            onClick={handleSubmit}
            disabled={!message.trim() || submitting}
            size="sm"
            className="w-full"
          >
            {submitting ? "Sending..." : "Send Feedback"}
          </Button>
        </div>
      )}
    </>
  );
}
