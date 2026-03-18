// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState, useEffect } from "react";
import { Loader2, Monitor, Send, ListTodo } from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription, SheetTrigger } from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { useCreateSubmission } from "@/lib/hooks/use-builder";

interface ExchangeCodeResponse {
  code: string;
  expires_in: number;
  builder_url: string;
}

export default function BuilderPage() {
  const { user } = useAuth();
  const [builderUrl, setBuilderUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  const [publishOpen, setPublishOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    category: "general",
    credits: 10,
    tags: "",
    langflow_flow_id: "",
  });
  const createSubmission = useCreateSubmission();

  async function handlePublish(e: React.FormEvent) {
    e.preventDefault();
    try {
      await createSubmission.mutateAsync({
        name: formData.name,
        description: formData.description || undefined,
        category: formData.category,
        credits: formData.credits,
        tags: formData.tags ? formData.tags.split(",").map(t => t.trim()).filter(Boolean) : [],
        langflow_flow_id: formData.langflow_flow_id,
      });
      setPublishOpen(false);
      setFormData({ name: "", description: "", category: "general", credits: 10, tags: "", langflow_flow_id: "" });
      toast.success("Submission created! The CrewHub team will review your agent.");
    } catch (error: any) {
      toast.error(error?.message || "Failed to submit. Please try again.");
    }
  }

  useEffect(() => {
    setIsMobile(window.innerWidth < 768);
  }, []);

  useEffect(() => {
    if (!user) {
      setLoading(false);
      return;
    }

    async function getBuilderAccess() {
      try {
        // Use builder.crewhubai.com proxy — same domain as parent,
        // so cookies work in iframe (third-party cookies blocked cross-origin)
        setBuilderUrl("https://builder.crewhubai.com");
      } catch {
        setError("Failed to load builder. Please try again.");
      } finally {
        setLoading(false);
      }
    }

    getBuilderAccess();
  }, [user]);

  if (isMobile) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
        <Monitor className="h-12 w-12 text-muted-foreground" />
        <h2 className="text-lg font-semibold">Desktop Recommended</h2>
        <p className="max-w-sm text-sm text-muted-foreground">
          The visual agent builder works best on a desktop or tablet screen.
          Please switch to a larger device.
        </p>
      </div>
    );
  }

  if (!user && !loading) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 px-4 text-center">
        <h2 className="text-lg font-semibold">Sign in to Build Agents</h2>
        <p className="max-w-sm text-sm text-muted-foreground">
          Create AI agents visually with our drag-and-drop builder. Sign in to get started with 3 free agents.
        </p>
        <a
          href="/login?redirect=/dashboard/builder"
          className="rounded-lg bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground"
        >
          Sign In
        </a>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4">
        <p className="text-destructive">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="rounded-lg bg-primary px-4 py-2 text-sm text-primary-foreground"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between border-b bg-card px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-semibold">CrewHub Agent Builder</h1>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
            Beta
          </span>
        </div>
        <div className="flex items-center gap-4">
          <p className="hidden text-xs text-muted-foreground sm:block">
            Create a flow, then use our custom CrewHub components to build your agent
          </p>
          <a
            href="/dashboard/builder/submissions"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ListTodo className="h-4 w-4" />
            My Submissions
          </a>
          <Sheet open={publishOpen} onOpenChange={setPublishOpen}>
            <SheetTrigger asChild>
              <Button size="sm">
                <Send className="mr-2 h-4 w-4" />
                Publish
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Publish to Marketplace</SheetTitle>
                <SheetDescription>
                  Submit your Langflow agent for review. The CrewHub team will review and list it on the marketplace.
                </SheetDescription>
              </SheetHeader>
              <form onSubmit={handlePublish} className="mt-6 space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="name">Agent Name *</Label>
                  <Input
                    id="name"
                    required
                    maxLength={200}
                    value={formData.name}
                    onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., Marketing Email Writer"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="What does your agent do?"
                    rows={3}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="category">Category</Label>
                  <Select
                    value={formData.category}
                    onValueChange={(v) => setFormData(prev => ({ ...prev, category: v }))}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {["general", "engineering", "design", "marketing", "content", "data", "testing", "support", "business", "research"].map(c => (
                        <SelectItem key={c} value={c}>
                          {c.charAt(0).toUpperCase() + c.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="credits">Credits per task</Label>
                  <Input
                    id="credits"
                    type="number"
                    min={5}
                    value={formData.credits}
                    onChange={(e) => setFormData(prev => ({ ...prev, credits: Number(e.target.value) }))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tags">Tags (comma separated)</Label>
                  <Input
                    id="tags"
                    value={formData.tags}
                    onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
                    placeholder="e.g., email, marketing, copywriting"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="flow_id">Langflow Flow ID *</Label>
                  <Input
                    id="flow_id"
                    required
                    maxLength={200}
                    value={formData.langflow_flow_id}
                    onChange={(e) => setFormData(prev => ({ ...prev, langflow_flow_id: e.target.value }))}
                    placeholder="Paste from your Langflow URL"
                  />
                  <p className="text-xs text-muted-foreground">
                    Find this in the Langflow URL: /flow/[flow-id]
                  </p>
                </div>
                <div className="flex gap-3 pt-2">
                  <Button type="button" variant="outline" onClick={() => setPublishOpen(false)}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={createSubmission.isPending || !formData.name || !formData.langflow_flow_id}
                  >
                    {createSubmission.isPending ? "Submitting..." : "Submit for Review"}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Submissions are reviewed by the CrewHub team. Check status on your submissions page.
                </p>
              </form>
            </SheetContent>
          </Sheet>
          <span className="text-[10px] text-muted-foreground/50">
            Powered by Langflow
          </span>
        </div>
      </div>

      {/* Langflow iframe */}
      {builderUrl && (
        <iframe
          src={builderUrl}
          className="flex-1 border-0"
          allow="clipboard-read; clipboard-write"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
          title="CrewHub Agent Builder"
        />
      )}
    </div>
  );
}
