"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
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
  });

  function update(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
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
    };

    try {
      const agent = await createAgent.mutateAsync(data);
      toast.success("Agent registered successfully");
      router.push(ROUTES.agentDetail(agent.id));
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
                <Label>Agent Name</Label>
                <Input
                  value={form.name}
                  onChange={(e) => update("name", e.target.value)}
                  placeholder="My Agent"
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={form.description}
                  onChange={(e) => update("description", e.target.value)}
                  placeholder="What does this agent do?"
                  rows={4}
                />
              </div>
              <div className="space-y-2">
                <Label>Endpoint URL</Label>
                <Input
                  value={form.endpoint}
                  onChange={(e) => update("endpoint", e.target.value)}
                  placeholder="https://my-agent.example.com/a2a"
                />
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
              <Button onClick={() => setStep((s) => s + 1)}>
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
