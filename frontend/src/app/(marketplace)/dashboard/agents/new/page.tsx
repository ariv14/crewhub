// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, Plus, X } from "lucide-react";
import Link from "next/link";
import { useCreateAgent } from "@/lib/hooks/use-agents";
import { ROUTES, CATEGORIES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import type { AgentCreate } from "@/types/agent";

const STEPS = ["Basic Info", "Skills", "Pricing", "Review"];

export default function NewAgentPage() {
  const router = useRouter();
  const createAgent = useCreateAgent();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    name: "",
    description: "",
    endpoint: "",
    version: "1.0.0",
    category: "general",
    tags: "",
    creditsPerTask: "10",
    billingModel: "per_task",
    licenseType: "commercial",
    mcpServerUrl: "",
    avatarUrl: "",
    conversationStarters: [""],
  });

  function update(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  const [errors, setErrors] = useState<Record<string, string>>({});

  function validateStep(s: number): boolean {
    const errs: Record<string, string> = {};
    if (s === 0) {
      if (!form.name.trim()) errs.name = "Agent name is required";
      if (!form.description.trim()) errs.description = "Description is required";
      if (!form.endpoint.trim()) errs.endpoint = "Endpoint URL is required";
      else if (!/^https?:\/\/.+/.test(form.endpoint.trim()))
        errs.endpoint = "Must be a valid URL starting with http:// or https://";
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  async function handleSubmit() {
    const data: AgentCreate = {
      name: form.name,
      description: form.description,
      endpoint: form.endpoint,
      version: form.version,
      category: form.category,
      tags: form.tags
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean),
      capabilities: {},
      skills: [],
      security_schemes: [],
      pricing: {
        license_type: form.licenseType as AgentCreate["pricing"]["license_type"],
        tiers: [],
        model: form.billingModel,
        credits: Number(form.creditsPerTask),
        trial_days: null,
        trial_task_limit: null,
      },
      accepted_payment_methods: ["credits"],
      mcp_server_url: form.mcpServerUrl || undefined,
      avatar_url: form.avatarUrl || undefined,
      conversation_starters: form.conversationStarters.filter(Boolean),
    };

    try {
      const agent = await createAgent.mutateAsync(data);
      toast.success("Agent registered successfully");
      window.location.href = ROUTES.agentDetail(agent.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Registration failed");
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Button variant="ghost" size="sm" className="mb-4" asChild>
        <Link href={ROUTES.myAgents}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
      </Button>

      <h1 className="text-2xl font-bold">Register Agent</h1>
      <p className="mt-1 mb-6 text-muted-foreground">
        Register your AI agent on the CrewHub marketplace
      </p>

      {/* Step indicator */}
      <div className="mb-8 flex gap-2">
        {STEPS.map((s, i) => (
          <div
            key={s}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
              i === step
                ? "bg-primary text-primary-foreground"
                : i < step
                  ? "bg-primary/20 text-primary"
                  : "bg-muted text-muted-foreground"
            }`}
          >
            {i < step ? <Check className="h-3 w-3" /> : <span>{i + 1}</span>}
            {s}
          </div>
        ))}
      </div>

      <Card>
        <CardContent className="p-6">
          {step === 0 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Agent Name <span className="text-destructive">*</span></Label>
                <Input
                  value={form.name}
                  onChange={(e) => { update("name", e.target.value); setErrors((p) => ({ ...p, name: "" })); }}
                  placeholder="My Agent"
                  aria-invalid={!!errors.name}
                  className={errors.name ? "border-destructive" : ""}
                />
                {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
              </div>
              <div className="space-y-2">
                <Label>Description <span className="text-destructive">*</span></Label>
                <Textarea
                  value={form.description}
                  onChange={(e) => { update("description", e.target.value); setErrors((p) => ({ ...p, description: "" })); }}
                  placeholder="What does this agent do?"
                  rows={4}
                  aria-invalid={!!errors.description}
                  className={errors.description ? "border-destructive" : ""}
                />
                {errors.description && <p className="text-xs text-destructive">{errors.description}</p>}
              </div>
              <div className="space-y-2">
                <Label>Endpoint URL <span className="text-destructive">*</span></Label>
                <Input
                  value={form.endpoint}
                  onChange={(e) => { update("endpoint", e.target.value); setErrors((p) => ({ ...p, endpoint: "" })); }}
                  placeholder="https://my-agent.example.com/a2a"
                  aria-invalid={!!errors.endpoint}
                  className={errors.endpoint ? "border-destructive" : ""}
                />
                {errors.endpoint && <p className="text-xs text-destructive">{errors.endpoint}</p>}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Version</Label>
                  <Input
                    value={form.version}
                    onChange={(e) => update("version", e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select value={form.category} onValueChange={(v) => update("category", v)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((c) => (
                        <SelectItem key={c.slug} value={c.slug}>
                          {c.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Tags (comma-separated)</Label>
                <Input
                  value={form.tags}
                  onChange={(e) => update("tags", e.target.value)}
                  placeholder="nlp, summarization, code"
                />
              </div>
              <div className="space-y-2">
                <Label>MCP Server URL (optional)</Label>
                <Input
                  value={form.mcpServerUrl}
                  onChange={(e) => update("mcpServerUrl", e.target.value)}
                  placeholder="https://my-agent.example.com/mcp"
                />
                <p className="text-xs text-muted-foreground">
                  If your agent exposes an MCP server, provide the URL here
                </p>
              </div>
              <div className="space-y-2">
                <Label>Avatar URL (optional)</Label>
                <Input
                  value={form.avatarUrl}
                  onChange={(e) => update("avatarUrl", e.target.value)}
                  placeholder="https://example.com/avatar.png"
                />
              </div>
              <div className="space-y-2">
                <Label>Conversation Starters (optional)</Label>
                <p className="text-xs text-muted-foreground">
                  Suggested prompts users can click to try your agent
                </p>
                {form.conversationStarters.map((starter, i) => (
                  <div key={i} className="flex gap-2">
                    <Input
                      value={starter}
                      onChange={(e) => {
                        const next = [...form.conversationStarters];
                        next[i] = e.target.value;
                        setForm((f) => ({ ...f, conversationStarters: next }));
                      }}
                      placeholder={`Starter ${i + 1}`}
                    />
                    {form.conversationStarters.length > 1 && (
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          const next = form.conversationStarters.filter((_, j) => j !== i);
                          setForm((f) => ({ ...f, conversationStarters: next }));
                        }}
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
                {form.conversationStarters.length < 5 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setForm((f) => ({
                        ...f,
                        conversationStarters: [...f.conversationStarters, ""],
                      }))
                    }
                  >
                    <Plus className="mr-1 h-3 w-3" />
                    Add Starter
                  </Button>
                )}
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Skills can be configured after registration via the agent
                detail page or API. Continue to set up pricing.
              </p>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Credits per Task</Label>
                <Input
                  type="number"
                  min="0"
                  value={form.creditsPerTask}
                  onChange={(e) => update("creditsPerTask", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label>Billing Model</Label>
                <Select value={form.billingModel} onValueChange={(v) => update("billingModel", v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="per_task">Per Task</SelectItem>
                    <SelectItem value="per_token">Per Token</SelectItem>
                    <SelectItem value="per_minute">Per Minute</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>License Type</Label>
                <Select value={form.licenseType} onValueChange={(v) => update("licenseType", v)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="open">Open</SelectItem>
                    <SelectItem value="freemium">Freemium</SelectItem>
                    <SelectItem value="commercial">Commercial</SelectItem>
                    <SelectItem value="subscription">Subscription</SelectItem>
                    <SelectItem value="trial">Trial</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="space-y-3 text-sm">
              <h3 className="font-semibold">Review</h3>
              <div className="rounded border bg-muted/30 p-4 space-y-2">
                <p><strong>Name:</strong> {form.name}</p>
                <p><strong>Endpoint:</strong> {form.endpoint}</p>
                <p><strong>Category:</strong> {form.category}</p>
                <p><strong>Pricing:</strong> {form.creditsPerTask} credits/{form.billingModel.replace("per_", "")}</p>
                <p><strong>License:</strong> {form.licenseType}</p>
              </div>
            </div>
          )}

          <div className="mt-6 flex justify-between">
            <Button
              variant="outline"
              onClick={() => setStep((s) => s - 1)}
              disabled={step === 0}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button onClick={() => { if (validateStep(step)) setStep((s) => s + 1); }}>
                Next
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={createAgent.isPending}
              >
                {createAgent.isPending ? "Registering..." : "Register Agent"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
