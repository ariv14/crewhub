// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { Check, ChevronDown, ChevronRight, Copy, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Artifact } from "@/types/task";

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <Button variant="ghost" size="sm" onClick={handleCopy} className="h-7 gap-1.5 text-xs">
      {copied ? (
        <>
          <Check className="h-3 w-3" />
          Copied
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          Copy
        </>
      )}
    </Button>
  );
}

function ArtifactPart({
  part,
}: {
  part: {
    type: string;
    content: string | null;
    data: Record<string, unknown> | null;
    mime_type: string | null;
  };
}) {
  const [showRaw, setShowRaw] = useState(false);

  if (part.type === "text" && part.content) {
    return (
      <div className="space-y-2">
        <div className="prose prose-sm dark:prose-invert max-w-none prose-pre:bg-muted prose-pre:text-sm prose-code:text-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
            {part.content}
          </ReactMarkdown>
        </div>
        <div className="flex items-center gap-2 border-t pt-2">
          <CopyButton text={part.content} />
          <button
            type="button"
            onClick={() => setShowRaw(!showRaw)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
          >
            {showRaw ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            {showRaw ? "Hide raw" : "Show raw"}
          </button>
        </div>
        {showRaw && (
          <pre className="overflow-auto rounded bg-muted p-3 text-xs">
            {part.content}
          </pre>
        )}
      </div>
    );
  }

  if (
    part.type === "file" &&
    part.mime_type?.startsWith("image/") &&
    part.content
  ) {
    const isValidUrl = part.content.startsWith("https://");
    return (
      <div className="mt-2">
        {isValidUrl ? (
          <img
            src={part.content}
            alt="Artifact image"
            className="max-h-64 rounded border"
          />
        ) : (
          <p className="text-xs text-muted-foreground">[Image blocked: only HTTPS URLs allowed]</p>
        )}
      </div>
    );
  }

  if (part.type === "data" && part.data) {
    const json = JSON.stringify(part.data, null, 2);
    return (
      <div className="space-y-2">
        <pre className="overflow-auto rounded bg-muted p-3 text-xs">
          {json}
        </pre>
        <CopyButton text={json} />
      </div>
    );
  }

  return null;
}

interface TaskArtifactsDisplayProps {
  artifacts: Artifact[];
}

export function TaskArtifactsDisplay({ artifacts }: TaskArtifactsDisplayProps) {
  if (!artifacts || artifacts.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Output</h3>
      {artifacts.map((artifact, i) => (
        <div key={i} className="rounded-lg border p-4">
          {artifact.name && (
            <div className="mb-3 flex items-center gap-2 text-sm font-medium">
              <FileText className="h-4 w-4" />
              {artifact.name}
            </div>
          )}
          <div className="space-y-4">
            {artifact.parts.map((part, j) => (
              <ArtifactPart key={j} part={part} />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
