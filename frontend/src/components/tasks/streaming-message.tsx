// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { Brain, ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface StreamingMessageProps {
  /** Progressive text being streamed */
  streamedText: string;
  /** Agent thinking/reasoning text */
  thinkingText: string;
  /** Whether the stream is actively receiving data */
  isStreaming: boolean;
}

/**
 * Renders streaming agent output with a typing cursor effect.
 * Shows thinking text in a collapsible section and progressive markdown rendering.
 */
export function StreamingMessage({
  streamedText,
  thinkingText,
  isStreaming,
}: StreamingMessageProps) {
  const [showThinking, setShowThinking] = useState(false);

  return (
    <div className="space-y-3">
      {/* Thinking section */}
      {thinkingText && (
        <button
          type="button"
          onClick={() => setShowThinking((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          <Brain className="h-3.5 w-3.5 text-purple-400" />
          <span>Agent reasoning</span>
          {showThinking ? (
            <ChevronDown className="h-3 w-3" />
          ) : (
            <ChevronRight className="h-3 w-3" />
          )}
        </button>
      )}
      {showThinking && thinkingText && (
        <div className="rounded-md border border-purple-500/20 bg-purple-500/5 p-3 text-xs text-muted-foreground whitespace-pre-wrap">
          {thinkingText}
        </div>
      )}

      {/* Streaming text with typing cursor */}
      {streamedText && (
        <div className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-muted prose-pre:text-sm prose-code:text-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
            {streamedText}
          </ReactMarkdown>
          {isStreaming && (
            <span className="inline-block w-0.5 h-4 bg-primary animate-pulse ml-0.5 align-text-bottom" />
          )}
        </div>
      )}

      {/* Streaming indicator when no text yet */}
      {!streamedText && isStreaming && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="flex gap-1">
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:0ms]" />
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:150ms]" />
            <span className="h-1.5 w-1.5 rounded-full bg-primary animate-bounce [animation-delay:300ms]" />
          </div>
          <span>Agent is working...</span>
        </div>
      )}
    </div>
  );
}
