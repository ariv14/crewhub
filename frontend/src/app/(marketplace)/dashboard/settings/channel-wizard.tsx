// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import {
  Send,
  Hash,
  Gamepad2,
  Users,
  MessageCircle,
  ExternalLink,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Loader2,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { useCreateChannel } from "@/lib/hooks/use-channels";
import { useAgents } from "@/lib/hooks/use-agents";
import { useAuth } from "@/lib/auth-context";
import { PLATFORM_GUIDES, type PlatformKey } from "./platform-guides";
import type { ChannelPlatform } from "@/types/channel";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Send,
  Hash,
  Gamepad2,
  Users,
  MessageCircle,
};

const STEPS = ["Platform", "Credentials", "Agent & Budget", "Confirm"];

interface ChannelWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ChannelWizard({ open, onOpenChange }: ChannelWizardProps) {
  const { user } = useAuth();
  const createChannel = useCreateChannel();

  // Wizard state
  const [step, setStep] = useState(0);
  const [platform, setPlatform] = useState<PlatformKey | null>(null);
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({});
  const [botName, setBotName] = useState("");
  const [agentId, setAgentId] = useState("");
  const [skillId, setSkillId] = useState("");
  const [dailyCreditLimit, setDailyCreditLimit] = useState("");
  const [lowBalanceThreshold, setLowBalanceThreshold] = useState("10");
  const [pauseOnLimit, setPauseOnLimit] = useState(true);
  const [whatsappAck, setWhatsappAck] = useState(false);

  // Fetch user's agents for step 3
  const { data: agentsData } = useAgents({
    owner_id: user?.id,
    per_page: 100,
  });
  const agents = agentsData?.agents ?? [];
  const selectedAgent = agents.find((a) => a.id === agentId);
  const skills = selectedAgent?.skills ?? [];

  function reset() {
    setStep(0);
    setPlatform(null);
    setCredentials({});
    setShowPasswords({});
    setBotName("");
    setAgentId("");
    setSkillId("");
    setDailyCreditLimit("");
    setLowBalanceThreshold("10");
    setPauseOnLimit(true);
    setWhatsappAck(false);
  }

  function handleClose(open: boolean) {
    if (!open) reset();
    onOpenChange(open);
  }

  const guide = platform ? PLATFORM_GUIDES[platform] : null;

  // Validation per step
  function canProceed(): boolean {
    if (step === 0) return platform !== null;
    if (step === 1) {
      if (!guide) return false;
      if (!botName.trim()) return false;
      const allFilled = guide.credentials.every((c) => credentials[c.key]?.trim());
      if (!allFilled) return false;
      if (platform === "whatsapp" && !whatsappAck) return false;
      return true;
    }
    if (step === 2) return !!agentId;
    return true;
  }

  async function handleSubmit() {
    if (!platform || !guide) return;
    try {
      await createChannel.mutateAsync({
        platform: platform as ChannelPlatform,
        credentials,
        bot_name: botName.trim(),
        agent_id: agentId,
        skill_id: skillId || undefined,
        daily_credit_limit: dailyCreditLimit ? parseFloat(dailyCreditLimit) : undefined,
        low_balance_threshold: parseFloat(lowBalanceThreshold) || 10,
        pause_on_limit: pauseOnLimit,
      });
      toast.success(`${guide.name} channel created! Status: Pending verification.`);
      handleClose(false);
    } catch {
      toast.error("Failed to create channel. Please check your credentials and try again.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Connect a Channel</DialogTitle>
          <DialogDescription>
            {STEPS[step]} (Step {step + 1} of {STEPS.length})
          </DialogDescription>
        </DialogHeader>

        {/* Progress dots */}
        <div className="flex items-center justify-center gap-2">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-2 w-2 rounded-full transition-colors ${
                i === step
                  ? "bg-primary"
                  : i < step
                    ? "bg-primary/40"
                    : "bg-muted-foreground/20"
              }`}
            />
          ))}
        </div>

        {/* Step 1: Platform Selection */}
        {step === 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {(Object.entries(PLATFORM_GUIDES) as [PlatformKey, typeof PLATFORM_GUIDES[PlatformKey]][]).map(
              ([key, guide]) => {
                const Icon = ICONS[guide.icon];
                return (
                  <Card
                    key={key}
                    className={`cursor-pointer transition-colors hover:border-primary/50 ${
                      platform === key ? "border-primary bg-primary/5" : ""
                    }`}
                    onClick={() => setPlatform(key)}
                  >
                    <CardContent className="flex flex-col items-center gap-2 p-4">
                      {Icon && <Icon className="h-6 w-6" />}
                      <span className="text-sm font-medium">{guide.name}</span>
                      {guide.creditCost > 0 && (
                        <Badge variant="outline" className="text-[10px]">
                          +{guide.creditCost} credits/msg
                        </Badge>
                      )}
                    </CardContent>
                  </Card>
                );
              }
            )}
          </div>
        )}

        {/* Step 2: Credentials */}
        {step === 1 && guide && (
          <div className="space-y-4">
            {/* Bot name */}
            <div className="space-y-2">
              <Label>Bot Display Name</Label>
              <Input
                placeholder={`My ${guide.name} Bot`}
                value={botName}
                onChange={(e) => setBotName(e.target.value)}
              />
            </div>

            {/* Credential fields */}
            {guide.credentials.map((cred) => (
              <div key={cred.key} className="space-y-2">
                <Label>{cred.label}</Label>
                <div className="relative">
                  <Input
                    type={
                      cred.type === "password" && !showPasswords[cred.key]
                        ? "password"
                        : "text"
                    }
                    placeholder={cred.placeholder}
                    value={credentials[cred.key] ?? ""}
                    onChange={(e) =>
                      setCredentials((prev) => ({ ...prev, [cred.key]: e.target.value }))
                    }
                  />
                  {cred.type === "password" && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
                      onClick={() =>
                        setShowPasswords((prev) => ({
                          ...prev,
                          [cred.key]: !prev[cred.key],
                        }))
                      }
                    >
                      {showPasswords[cred.key] ? (
                        <EyeOff className="h-3.5 w-3.5" />
                      ) : (
                        <Eye className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  )}
                </div>
              </div>
            ))}

            {/* WhatsApp premium note */}
            {platform === "whatsapp" && "premiumNote" in guide && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                  <div className="space-y-2">
                    <p className="text-xs text-amber-700 dark:text-amber-400">
                      {(guide as typeof PLATFORM_GUIDES.whatsapp).premiumNote}
                    </p>
                    <label className="flex items-center gap-2 text-xs">
                      <input
                        type="checkbox"
                        checked={whatsappAck}
                        onChange={(e) => setWhatsappAck(e.target.checked)}
                        className="rounded"
                      />
                      I acknowledge the additional credit cost
                    </label>
                  </div>
                </div>
              </div>
            )}

            {/* Setup instructions (collapsible) */}
            <details className="rounded-lg border bg-card">
              <summary className="flex cursor-pointer items-center justify-between px-4 py-2.5 text-sm font-medium hover:bg-accent/50">
                Setup Instructions
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              </summary>
              <div className="border-t px-4 py-3 text-xs text-muted-foreground">
                <ol className="mb-3 list-decimal space-y-1 pl-4">
                  {guide.steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
                <a
                  href={guide.externalUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-primary hover:underline"
                >
                  {guide.externalLabel}
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </details>
          </div>
        )}

        {/* Step 3: Agent & Budget */}
        {step === 2 && (
          <div className="space-y-4">
            {/* Agent selection */}
            <div className="space-y-2">
              <Label>Agent</Label>
              <Select value={agentId} onValueChange={(v) => { setAgentId(v); setSkillId(""); }}>
                <SelectTrigger>
                  <SelectValue placeholder="Select an agent" />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {agents.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  No agents found. Register an agent first.
                </p>
              )}
            </div>

            {/* Skill selection (optional) */}
            {skills.length > 0 && (
              <div className="space-y-2">
                <Label>Skill (Optional)</Label>
                <Select value={skillId} onValueChange={setSkillId}>
                  <SelectTrigger>
                    <SelectValue placeholder="All skills (default)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All skills</SelectItem>
                    {skills.map((skill) => (
                      <SelectItem key={skill.id} value={skill.id}>
                        {skill.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Limit channel to a specific skill, or leave blank to let the agent decide.
                </p>
              </div>
            )}

            {/* Budget controls */}
            <div className="space-y-3 rounded-lg border p-3">
              <p className="text-sm font-medium">Budget Controls</p>
              <div className="space-y-2">
                <Label className="text-xs">Daily Credit Limit</Label>
                <Input
                  type="number"
                  min="0"
                  step="10"
                  placeholder="No limit"
                  value={dailyCreditLimit}
                  onChange={(e) => setDailyCreditLimit(e.target.value)}
                  className="max-w-[200px]"
                />
              </div>
              <div className="space-y-2">
                <Label className="text-xs">Low Balance Alert Threshold</Label>
                <Input
                  type="number"
                  min="0"
                  step="5"
                  placeholder="10"
                  value={lowBalanceThreshold}
                  onChange={(e) => setLowBalanceThreshold(e.target.value)}
                  className="max-w-[200px]"
                />
              </div>
              <label className="flex items-center gap-2 text-xs">
                <input
                  type="checkbox"
                  checked={pauseOnLimit}
                  onChange={(e) => setPauseOnLimit(e.target.checked)}
                  className="rounded"
                />
                Pause channel when daily credit limit is reached
              </label>
            </div>
          </div>
        )}

        {/* Step 4: Confirmation */}
        {step === 3 && guide && (
          <div className="space-y-4">
            <div className="rounded-lg border bg-muted/30 p-4 space-y-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-5 w-5 text-green-500" />
                <span className="text-sm font-medium">Ready to connect</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <span className="text-muted-foreground">Platform</span>
                <span className="font-medium">{guide.name}</span>
                <span className="text-muted-foreground">Bot Name</span>
                <span className="font-medium">{botName}</span>
                <span className="text-muted-foreground">Agent</span>
                <span className="font-medium">{selectedAgent?.name ?? "—"}</span>
                {skillId && (
                  <>
                    <span className="text-muted-foreground">Skill</span>
                    <span className="font-medium">
                      {skills.find((s) => s.id === skillId)?.name ?? "—"}
                    </span>
                  </>
                )}
                <span className="text-muted-foreground">Daily Limit</span>
                <span className="font-medium">
                  {dailyCreditLimit ? `${dailyCreditLimit} credits` : "No limit"}
                </span>
              </div>
            </div>

            {/* Webhook URL note */}
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
              <p className="text-xs text-blue-700 dark:text-blue-400">
                {guide.webhookManagement === "automatic" ? (
                  <>Webhook URL will be configured automatically after channel creation.</>
                ) : (
                  <>
                    After creation, you will need to configure the webhook URL in your{" "}
                    {guide.name} app settings. The URL will be shown on the channel card.
                  </>
                )}
              </p>
            </div>

            <div className="rounded-lg border border-muted-foreground/20 bg-muted/20 p-3">
              <p className="text-xs text-muted-foreground">
                Your channel will start in <Badge variant="secondary" className="text-[10px]">Pending</Badge>{" "}
                status while we verify the credentials and set up the connection.
                This usually takes a few seconds.
              </p>
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex items-center justify-between pt-2">
          <Button
            variant="ghost"
            onClick={() => setStep((s) => Math.max(0, s - 1))}
            disabled={step === 0}
          >
            <ChevronLeft className="mr-1 h-4 w-4" />
            Back
          </Button>
          {step < STEPS.length - 1 ? (
            <Button onClick={() => setStep((s) => s + 1)} disabled={!canProceed()}>
              Next
              <ChevronRight className="ml-1 h-4 w-4" />
            </Button>
          ) : (
            <Button
              onClick={handleSubmit}
              disabled={createChannel.isPending}
            >
              {createChannel.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Create Channel
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
