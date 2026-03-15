// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface TaskRatingFormProps {
  onSubmit: (score: number, comment: string) => void;
  loading?: boolean;
}

export function TaskRatingForm({ onSubmit, loading }: TaskRatingFormProps) {
  const [score, setScore] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <h4 className="text-sm font-semibold">Rate this task</h4>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((s) => (
          <button
            key={s}
            type="button"
            onMouseEnter={() => setHover(s)}
            onMouseLeave={() => setHover(0)}
            onClick={() => setScore(s)}
          >
            <Star
              className={cn(
                "h-6 w-6 transition-colors",
                (hover || score) >= s
                  ? "fill-yellow-400 text-yellow-400"
                  : "text-muted-foreground"
              )}
            />
          </button>
        ))}
      </div>
      <Textarea
        placeholder="Optional comment..."
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
      />
      <Button
        size="sm"
        disabled={score === 0 || loading}
        onClick={() => onSubmit(score, comment)}
      >
        {loading ? "Submitting..." : "Submit Rating"}
      </Button>
    </div>
  );
}
