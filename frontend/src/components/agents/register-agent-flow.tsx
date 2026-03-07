"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  Globe,
  LogIn,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useDetectAgent, useCreateAgent } from "@/lib/hooks/use-agents";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api-client";
import { ROUTES, CATEGORIES } from "@/lib/constants";
import type { DetectResponse, AgentCreate } from "@/types/agent";

type Step = "paste" | "review" | "success";

export function RegisterAgentFlow() {
  const router = useRouter();
  const { user, loginWithGoogle, loading: authLoading } = useAuth();
  const detectMutation = useDetectAgent();
  const createMutation = useCreateAgent();

  const [step, setStep] = useState<Step>("paste");
  const [url, setUrl] = useState("");
  const [detected, setDetected] = useState<DetectResponse | null>(null);
  const [registeredId, setRegisteredId] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);

  // Editable fields
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("");
  const [category, setCategory] = useState("general");
  const [licenseType, setLicenseType] = useState("open");
  const [credits, setCredits] = useState("1");
  const [billingModel, setBillingModel] = useState("per_task");

  async function handleDetect() {
    if (!url.trim()) return;
    try {
      const result = await detectMutation.mutateAsync(url.trim());
      setDetected(result);
      setName(result.name);
      setDescription(result.description);
      setVersion(result.version || "1.0.0");
      if (result.suggested_registration.category) {
        setCategory(result.suggested_registration.category);
      }
      setStep("review");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Detection failed";
      toast.error(message);
    }
  }

  async function handleSignIn() {
    setSigningIn(true);
    try {
      await loginWithGoogle();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Sign in failed"
      );
    } finally {
      setSigningIn(false);
    }
  }

  async function handleRegister() {
    if (!detected) return;

    const data: AgentCreate = {
      ...detected.suggested_registration,
      name,
      description: description || `Agent: ${name}`,
      version,
      category,
      pricing: {
        license_type: licenseType as AgentCreate["pricing"]["license_type"],
        tiers: [],
        model: billingModel,
        credits: Number(credits),
        trial_days: null,
        trial_task_limit: null,
      },
    };

    try {
      const agent = await createMutation.mutateAsync(data);
      setRegisteredId(agent.id);
      setStep("success");
      // Mark onboarding as completed for developer path
      try {
        await api.post("/auth/onboarding", { interests: ["developer"] });
      } catch {
        // Non-critical — agent is already registered
      }
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : "Registration failed"
      );
    }
  }

  const stepLabels = ["Paste URL", "Review & Register", "Live"];
  const stepIndex = step === "paste" ? 0 : step === "review" ? 1 : 2;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Register Your Agent</h1>
        <p className="mt-1 text-muted-foreground">
          Paste your agent&apos;s endpoint URL and we&apos;ll auto-detect its
          capabilities
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex gap-2">
        {stepLabels.map((label, i) => (
          <span
            key={label}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              i === stepIndex
                ? "bg-primary text-primary-foreground"
                : i < stepIndex
                  ? "bg-primary/20 text-primary"
                  : "bg-muted text-muted-foreground"
            }`}
          >
            {label}
          </span>
        ))}
      </div>

      <Card>
        <CardContent className="p-6">
          {/* Step 1: Paste URL */}
          {step === "paste" && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold">Agent Endpoint</h2>
                <p className="text-sm text-muted-foreground">
                  We&apos;ll read your{" "}
                  <code className="rounded bg-muted px-1 text-xs">
                    /.well-known/agent-card.json
                  </code>
                </p>
              </div>

              <div className="space-y-2">
                <Label>Endpoint URL</Label>
                <div className="flex gap-2">
                  <Input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://my-agent.example.com"
                    onKeyDown={(e) => {
                      if (e.key === "Enter") handleDetect();
                    }}
                    data-testid="detect-url-input"
                    className="flex-1"
                  />
                  <Button
                    onClick={handleDetect}
                    disabled={!url.trim() || detectMutation.isPending}
                    data-testid="detect-button"
                  >
                    {detectMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Globe className="mr-2 h-4 w-4" />
                    )}
                    Detect Agent
                  </Button>
                </div>
              </div>

              {detectMutation.error && (
                <div className="flex items-start gap-2 rounded border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>
                    {detectMutation.error instanceof Error
                      ? detectMutation.error.message
                      : "Detection failed"}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Review & Register */}
          {step === "review" && detected && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h2 className="text-lg font-semibold">Review & Register</h2>
                <p className="text-sm text-muted-foreground">
                  Detected from your agent card. Edit as needed.
                </p>
              </div>

              {detected.warnings.length > 0 && (
                <div className="flex items-start gap-2 rounded border border-yellow-500/50 bg-yellow-500/10 p-3 text-sm text-yellow-600 dark:text-yellow-400">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <div>
                    {detected.warnings.map((w, i) => (
                      <p key={i}>{w}</p>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  data-testid="review-name"
                />
              </div>

              <div className="space-y-2">
                <Label>Description</Label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Version</Label>
                  <Input
                    value={version}
                    onChange={(e) => setVersion(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Category</Label>
                  <Select value={category} onValueChange={setCategory}>
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

              {detected.skills.length > 0 && (
                <div className="space-y-2">
                  <Label>Detected Skills ({detected.skills.length})</Label>
                  <div className="flex flex-wrap gap-2">
                    {detected.skills.map((s) => (
                      <Badge key={s.skill_key} variant="secondary">
                        {s.name}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="space-y-3 rounded border bg-muted/30 p-4">
                <h3 className="text-sm font-semibold">Pricing</h3>
                <div className="grid grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs">License</Label>
                    <Select
                      value={licenseType}
                      onValueChange={setLicenseType}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="open">Open</SelectItem>
                        <SelectItem value="freemium">Freemium</SelectItem>
                        <SelectItem value="commercial">Commercial</SelectItem>
                        <SelectItem value="subscription">
                          Subscription
                        </SelectItem>
                        <SelectItem value="trial">Trial</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Credits/Task</Label>
                    <Input
                      type="number"
                      min="0"
                      value={credits}
                      onChange={(e) => setCredits(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Billing</Label>
                    <Select
                      value={billingModel}
                      onValueChange={setBillingModel}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="per_task">Per Task</SelectItem>
                        <SelectItem value="per_token">Per Token</SelectItem>
                        <SelectItem value="per_minute">
                          Per Minute
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              {/* Sign-in gate */}
              {!user && !authLoading && (
                <div className="rounded border border-primary/30 bg-primary/5 p-4">
                  <p className="mb-3 text-sm font-medium">
                    Sign in to register your agent
                  </p>
                  <Button onClick={handleSignIn} disabled={signingIn}>
                    {signingIn ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <LogIn className="mr-2 h-4 w-4" />
                    )}
                    Sign in with Google
                  </Button>
                </div>
              )}

              <div className="flex justify-between">
                <Button variant="outline" onClick={() => setStep("paste")}>
                  Back
                </Button>
                <Button
                  onClick={handleRegister}
                  disabled={!name.trim() || !user || createMutation.isPending}
                  data-testid="register-button"
                >
                  {createMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Register Agent
                </Button>
              </div>
            </div>
          )}

          {/* Step 3: Success */}
          {step === "success" && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <div className="rounded-full bg-green-500/10 p-4">
                <CheckCircle2 className="h-10 w-10 text-green-500" />
              </div>
              <h2 className="text-xl font-semibold">Agent Registered!</h2>
              <p className="text-sm text-muted-foreground">
                Your agent <strong>{name}</strong> is now live on the
                marketplace.
              </p>
              <Button
                onClick={() => {
                  // Full page navigation — the new agent isn't in
                  // generateStaticParams so client-side router would 404.
                  window.location.href = registeredId
                    ? ROUTES.agentDetail(registeredId)
                    : ROUTES.agents;
                }}
                data-testid="view-agent-button"
              >
                View Agent
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
