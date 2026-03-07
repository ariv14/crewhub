"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { trackEvent } from "@/lib/telemetry";

interface FeedbackThumbsProps {
  context: string; // e.g., "suggestion", "task_result"
  contextId?: string; // e.g., suggestion ID or task ID
  className?: string;
}

export function FeedbackThumbs({
  context,
  contextId,
  className,
}: FeedbackThumbsProps) {
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null);

  function handleFeedback(value: "up" | "down") {
    setFeedback(value);
    trackEvent("suggestion_feedback", {
      context,
      context_id: contextId,
      feedback: value,
    });
  }

  return (
    <div className={cn("flex items-center gap-1", className)}>
      <span className="text-xs text-muted-foreground mr-1">Helpful?</span>
      <Button
        variant="ghost"
        size="icon"
        className={cn(
          "h-7 w-7",
          feedback === "up" && "text-green-500 bg-green-500/10"
        )}
        onClick={() => handleFeedback("up")}
        disabled={feedback !== null}
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className={cn(
          "h-7 w-7",
          feedback === "down" && "text-red-500 bg-red-500/10"
        )}
        onClick={() => handleFeedback("down")}
        disabled={feedback !== null}
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </Button>
      {feedback && (
        <span className="text-xs text-muted-foreground ml-1">Thanks!</span>
      )}
    </div>
  );
}
