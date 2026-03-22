// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatRelativeTime } from "@/lib/utils";
import { useChannelMessages } from "@/lib/hooks/use-channels";
import type { ChannelMessage } from "@/types/channel";

type DirectionFilter = "all" | "inbound" | "outbound";

interface MessageLogProps {
  channelId: string;
  userHash?: string;
}

function DirectionBadge({ direction }: { direction: ChannelMessage["direction"] }) {
  if (direction === "inbound") {
    return (
      <Badge variant="outline" className="shrink-0 text-green-400 border-green-500/40 bg-green-500/10">
        IN
      </Badge>
    );
  }
  if (direction === "outbound") {
    return (
      <Badge variant="outline" className="shrink-0 text-blue-400 border-blue-500/40 bg-blue-500/10">
        OUT
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="shrink-0 text-muted-foreground">
      SYS
    </Badge>
  );
}

export function MessageLog({ channelId }: MessageLogProps) {
  const [filter, setFilter] = useState<DirectionFilter>("all");
  const { data, isLoading } = useChannelMessages(
    channelId,
    filter === "all" ? undefined : filter
  );

  const filterButtons: { key: DirectionFilter; label: string }[] = [
    { key: "all", label: "All" },
    { key: "inbound", label: "Inbound" },
    { key: "outbound", label: "Outbound" },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1">
        {filterButtons.map(({ key, label }) => (
          <Button
            key={key}
            variant={filter === key ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setFilter(key)}
          >
            {label}
          </Button>
        ))}
      </div>

      {isLoading && (
        <p className="py-8 text-center text-sm text-muted-foreground">Loading messages…</p>
      )}

      {!isLoading && !data?.messages.length && (
        <p className="py-8 text-center text-sm text-muted-foreground">No messages yet</p>
      )}

      {!isLoading && data?.messages.length ? (
        <div className="space-y-2">
          {data.messages.map((msg) => (
            <div
              key={msg.id}
              className="flex items-start gap-3 rounded-lg border bg-card px-4 py-3"
            >
              <DirectionBadge direction={msg.direction} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
                  <span className="font-mono">{msg.platform_user_id_hash.slice(0, 8)}…</span>
                  <span>·</span>
                  <span>{formatRelativeTime(msg.created_at)}</span>
                </div>
                {msg.direction === "inbound" ? (
                  <p className="text-sm italic text-muted-foreground">
                    [Content not stored — privacy policy]
                  </p>
                ) : (
                  <p className="text-sm">{msg.message_text ?? <span className="italic text-muted-foreground">[empty]</span>}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {data?.has_more && (
        <div className="flex justify-center pt-2">
          <Button variant="outline" size="sm" disabled>
            Load more
          </Button>
        </div>
      )}
    </div>
  );
}
