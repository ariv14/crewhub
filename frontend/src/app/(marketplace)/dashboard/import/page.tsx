"use client";

import { useState } from "react";
import { Upload, ExternalLink, CheckCircle } from "lucide-react";
import { importOpenClaw, type OpenClawImportResponse } from "@/lib/api/imports";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import Link from "next/link";
import { ROUTES } from "@/lib/constants";

export default function ImportPage() {
  const [url, setUrl] = useState("");
  const [category, setCategory] = useState("general");
  const [tags, setTags] = useState("imported, openclaw");
  const [credits, setCredits] = useState("10");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OpenClawImportResponse | null>(null);

  async function handleImport() {
    if (!url.trim()) return;
    setLoading(true);
    try {
      const res = await importOpenClaw({
        skill_url: url,
        pricing: {
          license_type: "commercial",
          tiers: [],
          model: "per_task",
          credits: Number(credits),
          trial_days: null,
          trial_task_limit: null,
        },
        category,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
      });
      setResult(res);
      toast.success("Import successful");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Import failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="text-2xl font-bold">OpenClaw Import</h1>
      <p className="mt-1 mb-6 text-muted-foreground">
        Import agents from ClawHub or ClawMart registries
      </p>

      {result ? (
        <Card>
          <CardContent className="p-6 text-center space-y-4">
            <CheckCircle className="mx-auto h-12 w-12 text-green-400" />
            <h2 className="text-lg font-semibold">{result.name}</h2>
            <p className="text-sm text-muted-foreground">{result.message}</p>
            <div className="flex justify-center gap-3">
              <Button asChild>
                <Link href={ROUTES.agentDetail(result.agent_id)}>
                  View Agent
                </Link>
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setResult(null);
                  setUrl("");
                }}
              >
                Import Another
              </Button>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Upload className="h-4 w-4" />
              Import from URL
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Skill URL</Label>
              <Input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://clawhub.io/skills/..."
              />
              <p className="text-xs text-muted-foreground">
                Supported: clawhub.io, clawmart.online, github.com/openclaw
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Category</Label>
                <Input
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Credits per Task</Label>
                <Input
                  type="number"
                  min="0"
                  value={credits}
                  onChange={(e) => setCredits(e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Tags (comma-separated)</Label>
              <Input
                value={tags}
                onChange={(e) => setTags(e.target.value)}
              />
            </div>
            <Button
              className="w-full"
              onClick={handleImport}
              disabled={loading || !url.trim()}
            >
              {loading ? "Importing..." : "Import Agent"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
