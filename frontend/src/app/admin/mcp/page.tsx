"use client";

import { useState } from "react";
import { Loader2, Play, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { JsonViewer } from "@/components/shared/json-viewer";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

function getPageAuthHeaders(): Record<string, string> {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  if (!token) return {};
  if (token.startsWith("a2a_")) return { "X-API-Key": token };
  return { Authorization: `Bearer ${token}` };
}

interface McpTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export default function McpPlaygroundPage() {
  const [tools, setTools] = useState<McpTool[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [params, setParams] = useState("{}");
  const [result, setResult] = useState<unknown>(null);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchTools() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/mcp`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getPageAuthHeaders() },
        body: JSON.stringify({ jsonrpc: "2.0", method: "tools/list", id: 1 }),
      });
      const data = await res.json();
      setTools(data.result?.tools || []);
    } catch (e) {
      setError(`Failed to fetch tools: ${e}`);
    } finally {
      setLoading(false);
    }
  }

  async function executeTool() {
    if (!selectedTool) return;
    setExecuting(true);
    setError(null);
    setResult(null);
    try {
      const parsedParams = JSON.parse(params);
      const res = await fetch(`${API_BASE}/mcp`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getPageAuthHeaders() },
        body: JSON.stringify({
          jsonrpc: "2.0",
          method: "tools/call",
          params: { name: selectedTool, arguments: parsedParams },
          id: 2,
        }),
      });
      const data = await res.json();
      setResult(data.result || data.error);
    } catch (e) {
      setError(`Execution failed: ${e}`);
    } finally {
      setExecuting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">MCP Playground</h1>
          <p className="text-muted-foreground">
            Test MCP tool calls against CrewHub&apos;s /mcp endpoint
          </p>
        </div>
        <Button onClick={fetchTools} disabled={loading}>
          {loading ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          {tools.length ? "Refresh Tools" : "Load Tools"}
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {tools.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-2">
          {/* Tool list */}
          <div className="space-y-3">
            <h2 className="font-semibold">
              Available Tools ({tools.length})
            </h2>
            <div className="max-h-[500px] space-y-2 overflow-y-auto">
              {tools.map((tool) => (
                <button
                  key={tool.name}
                  onClick={() => {
                    setSelectedTool(tool.name);
                    setParams("{}");
                    setResult(null);
                  }}
                  className={`w-full rounded-lg border p-3 text-left transition-colors ${
                    selectedTool === tool.name
                      ? "border-primary bg-primary/5"
                      : "hover:bg-muted/50"
                  }`}
                >
                  <p className="font-mono text-sm font-medium">
                    {tool.name}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
                    {tool.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Tool execution */}
          <div className="space-y-4">
            {selectedTool && (
              <>
                <h2 className="font-semibold">
                  Execute: <code>{selectedTool}</code>
                </h2>
                <div>
                  <label className="mb-1 block text-sm font-medium">
                    Parameters (JSON)
                  </label>
                  <textarea
                    value={params}
                    onChange={(e) => setParams(e.target.value)}
                    className="h-32 w-full rounded-lg border bg-muted/30 p-3 font-mono text-sm"
                    placeholder='{"key": "value"}'
                  />
                </div>
                <Button onClick={executeTool} disabled={executing}>
                  {executing ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="mr-2 h-4 w-4" />
                  )}
                  Execute
                </Button>

                {result && (
                  <div className="mt-4">
                    <h3 className="mb-2 text-sm font-medium">Result</h3>
                    <JsonViewer data={result} title="Response" />
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
