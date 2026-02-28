import { Download, FileText, Image as ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Artifact } from "@/types/task";

interface TaskArtifactsDisplayProps {
  artifacts: Artifact[];
}

export function TaskArtifactsDisplay({ artifacts }: TaskArtifactsDisplayProps) {
  if (!artifacts || artifacts.length === 0) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold">Artifacts</h3>
      {artifacts.map((artifact, i) => (
        <div key={i} className="rounded-lg border p-4">
          {artifact.name && (
            <div className="mb-3 flex items-center justify-between">
              <span className="flex items-center gap-2 text-sm font-medium">
                <FileText className="h-4 w-4" />
                {artifact.name}
              </span>
            </div>
          )}
          {artifact.parts.map((part, j) => {
            if (part.type === "text" && part.content) {
              return (
                <div key={j} className="prose prose-sm dark:prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap rounded bg-muted p-3 text-sm">
                    {part.content}
                  </pre>
                </div>
              );
            }
            if (
              part.type === "file" &&
              part.mime_type?.startsWith("image/") &&
              part.content
            ) {
              return (
                <div key={j} className="mt-2">
                  <img
                    src={part.content}
                    alt={artifact.name ?? "Artifact image"}
                    className="max-h-64 rounded border"
                  />
                </div>
              );
            }
            if (part.type === "data" && part.data) {
              return (
                <pre
                  key={j}
                  className="mt-2 overflow-auto rounded bg-muted p-3 text-xs"
                >
                  {JSON.stringify(part.data, null, 2)}
                </pre>
              );
            }
            return null;
          })}
        </div>
      ))}
    </div>
  );
}
