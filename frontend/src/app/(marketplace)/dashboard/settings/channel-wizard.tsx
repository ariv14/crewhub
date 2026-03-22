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
  ChevronLeft,
  ChevronRight,
  Loader2,
  Eye,
  EyeOff,
  AlertTriangle,
  CheckCircle2,
  Copy,
} from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { toast } from "sonner";
import { useCreateChannel } from "@/lib/hooks/use-channels";
import { useAgents } from "@/lib/hooks/use-agents";
import { useAuth } from "@/lib/auth-context";
import { PLATFORM_GUIDES, type PlatformKey } from "./platform-guides";
import type { Channel, ChannelPlatform } from "@/types/channel";

const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  Send,
  Hash,
  Gamepad2,
  Users,
  MessageCircle,
};

const SETUP_TIMES: Record<string, { time: string; difficulty: string; color: string }> = {
  telegram: { time: "~2 min", difficulty: "Easiest", color: "text-green-500" },
  slack: { time: "~10 min", difficulty: "Moderate", color: "text-yellow-500" },
  discord: { time: "~5 min", difficulty: "Moderate", color: "text-yellow-500" },
  teams: { time: "~15 min", difficulty: "Advanced", color: "text-orange-500" },
  whatsapp: { time: "~30 min", difficulty: "Advanced", color: "text-orange-500" },
};

const FORMAT_HINTS: Record<string, Record<string, string>> = {
  telegram: {
    bot_token: "Format: numbers:letters, 47+ characters",
  },
  slack: {
    bot_token: "Format: starts with xoxb-",
    signing_secret: "Format: 32-character hex string",
  },
  discord: {
    bot_token: "Format: starts with MTk or similar, 70+ characters",
    application_id: "Format: numeric, 17-20 digits",
  },
  teams: {
    app_id: "Format: UUID (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)",
    app_password: "Format: 34+ character secret",
  },
  whatsapp: {
    phone_number_id: "Format: numeric ID",
    access_token: "Format: starts with EAA, 50+ characters",
    verify_token: "Format: any string you choose",
  },
};

function validateTokenFormat(platform: string, key: string, value: string): "valid" | "warning" | "empty" {
  if (!value) return "empty";
  if (platform === "telegram" && key === "bot_token") {
    return /^\d+:[A-Za-z0-9_-]{35,}$/.test(value) ? "valid" : "warning";
  }
  if (platform === "slack" && key === "bot_token") {
    return value.startsWith("xoxb-") ? "valid" : "warning";
  }
  if (platform === "slack" && key === "signing_secret") {
    return /^[a-f0-9]{32}$/.test(value) ? "valid" : "warning";
  }
  if (platform === "discord" && key === "bot_token") {
    return value.length > 60 ? "valid" : "warning";
  }
  if (platform === "discord" && key === "application_id") {
    return /^\d{17,20}$/.test(value) ? "valid" : "warning";
  }
  if (platform === "teams" && key === "app_id") {
    return /^[a-f0-9-]{36}$/i.test(value) ? "valid" : "warning";
  }
  if (platform === "whatsapp" && key === "access_token") {
    return value.startsWith("EAA") && value.length > 50 ? "valid" : "warning";
  }
  return value.length > 10 ? "valid" : "warning";
}

const STEPS = ["Platform", "Setup & Credentials", "Agent", "Done"];

interface ChannelWizardProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  existingChannelCount?: number;
}

export function ChannelWizard({ open, onOpenChange, existingChannelCount = -1 }: ChannelWizardProps) {
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
  const [whatsappAck, setWhatsappAck] = useState(false);
  const [createdChannel, setCreatedChannel] = useState<Channel | null>(null);
  const [dailyLimit, setDailyLimit] = useState(100);
  const [lowBalance, setLowBalance] = useState(20);
  const [pauseOnLimit, setPauseOnLimit] = useState(true);
  const [privacyUrl, setPrivacyUrl] = useState("");

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
    setWhatsappAck(false);
    setCreatedChannel(null);
    setDailyLimit(100);
    setLowBalance(20);
    setPauseOnLimit(true);
    setPrivacyUrl("");
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
      if (!privacyUrl.trim() || !privacyUrl.startsWith("http")) return false;
      return true;
    }
    if (step === 2) return !!agentId;
    return true;
  }

  async function handleSubmit() {
    if (!platform || !guide) return;
    try {
      const channel = await createChannel.mutateAsync({
        platform: platform as ChannelPlatform,
        credentials,
        bot_name: botName.trim(),
        agent_id: agentId,
        skill_id: skillId || undefined,
        daily_credit_limit: dailyLimit || undefined,
        low_balance_threshold: lowBalance,
        pause_on_limit: pauseOnLimit,
        privacy_notice_url: privacyUrl.trim() || undefined,
      });
      setCreatedChannel(channel);
      setStep(3);
    } catch {
      toast.error("Failed to create channel. Please check your credentials and try again.");
    }
  }

  // Extract bot username from Telegram bot name or credentials
  const telegramBotUsername = platform === "telegram"
    ? botName.replace(/\s+/g, "").replace(/@/g, "")
    : "";

  return (
    <Sheet open={open} onOpenChange={handleClose}>
      <SheetContent side="right" className="w-full sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Connect a Channel</SheetTitle>
          <SheetDescription>
            {STEPS[step]} (Step {step + 1} of {STEPS.length})
          </SheetDescription>
        </SheetHeader>

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
          <div className="space-y-3">
            {existingChannelCount === 0 && (
              <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
                <p className="text-xs text-blue-700 dark:text-blue-400">
                  New to this? Start with Telegram -- it takes about 2 minutes.
                </p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-3">
              {(Object.entries(PLATFORM_GUIDES) as [PlatformKey, typeof PLATFORM_GUIDES[PlatformKey]][]).map(
                ([key, g]) => {
                  const Icon = ICONS[g.icon];
                  const setupTime = SETUP_TIMES[key];
                  return (
                    <Card
                      key={key}
                      className={`cursor-pointer transition-colors hover:border-primary/50 ${
                        platform === key ? "border-primary bg-primary/5" : ""
                      }`}
                      onClick={() => setPlatform(key)}
                    >
                      <CardContent className="flex flex-col items-center gap-1.5 p-4">
                        {Icon && <Icon className="h-6 w-6" />}
                        <span className="text-sm font-medium">{g.name}</span>
                        {setupTime && (
                          <p className="text-xs text-muted-foreground">{setupTime.time}</p>
                        )}
                        {setupTime && (
                          <Badge variant="outline" className={`text-[10px] ${setupTime.color}`}>
                            {setupTime.difficulty}
                          </Badge>
                        )}
                        {g.creditCost > 0 && (
                          <Badge variant="outline" className="text-[10px]">
                            +{g.creditCost} credits/msg
                          </Badge>
                        )}
                      </CardContent>
                    </Card>
                  );
                }
              )}
            </div>
            <div className="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2.5 text-xs text-amber-500/90">
              <span className="font-medium">⚠️ Healthcare Notice:</span>{" "}
              CrewHub channels must not be used to collect, store, or transmit Protected Health Information (PHI).
              No Business Associate Agreement (BAA) is in effect.
            </div>
          </div>
        )}

        {/* Step 2: Setup Instructions + Credentials */}
        {step === 1 && guide && platform && (
          <div className="space-y-5">
            {/* Setup instructions — PRIMARY content */}
            <div className="space-y-3">
              <p className="text-sm font-medium">Setup Instructions</p>
              <ol className="list-decimal space-y-2 pl-5 text-sm text-muted-foreground">
                {guide.steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
              <Button variant="outline" size="sm" asChild>
                <a
                  href={guide.externalUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2"
                >
                  {guide.externalLabel}
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </Button>
            </div>

            <div className="border-t" />

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
            <TooltipProvider>
              {guide.credentials.map((cred) => {
                const validation = validateTokenFormat(platform, cred.key, credentials[cred.key] ?? "");
                const hint = FORMAT_HINTS[platform]?.[cred.key];
                return (
                  <div key={cred.key} className="space-y-2">
                    <Label>{cred.label}</Label>
                    <div className="relative flex items-center gap-2">
                      <div className="relative flex-1">
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
                      {/* Validation indicator */}
                      {validation === "valid" && (
                        <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
                      )}
                      {validation === "warning" && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500 cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent>
                            <p className="text-xs">Token format doesn&apos;t match expected pattern.</p>
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </div>
                    {hint && (
                      <p className="text-xs text-muted-foreground">{hint}</p>
                    )}
                  </div>
                );
              })}
            </TooltipProvider>

            {/* Privacy Notice URL */}
            <div className="space-y-2">
              <Label htmlFor="privacy-url">Privacy Notice URL <span className="text-red-500">*</span></Label>
              <Input
                id="privacy-url"
                type="url"
                placeholder="https://example.com/privacy"
                value={privacyUrl}
                onChange={(e) => setPrivacyUrl(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                Required. Link to your privacy notice that informs users about data handling.
              </p>
            </div>

            {/* Data residency note */}
            <p className="mt-2 flex items-start gap-1.5 text-[11px] text-muted-foreground/70">
              <span>ℹ️</span>
              <span>Channel data is processed and stored in the United States. If your users are in the EU, ensure your privacy notice discloses this.</span>
            </p>

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
          </div>
        )}

        {/* Step 3: Agent selection */}
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
                  {agents.filter((agent) => agent.id).map((agent) => (
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
                <Select value={skillId || "__all__"} onValueChange={(v) => setSkillId(v === "__all__" ? "" : v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="All skills (default)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all__">All skills</SelectItem>
                    {skills.filter((skill) => skill.id).map((skill) => (
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
            <div className="space-y-4 rounded-lg border p-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Budget Controls</p>
              <div className="space-y-2">
                <Label htmlFor="daily-limit">Daily Credit Limit</Label>
                <Input
                  id="daily-limit"
                  type="number"
                  min={0}
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(Number(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">Max credits per day (0 = unlimited)</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="low-balance">Low Balance Alert</Label>
                <Input
                  id="low-balance"
                  type="number"
                  min={0}
                  value={lowBalance}
                  onChange={(e) => setLowBalance(Number(e.target.value))}
                />
                <p className="text-xs text-muted-foreground">Notify when account credits drop below</p>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="pause-on-limit">Auto-pause when daily limit reached</Label>
                </div>
                <Switch
                  id="pause-on-limit"
                  checked={pauseOnLimit}
                  onCheckedChange={setPauseOnLimit}
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Post-creation success screen */}
        {step === 3 && createdChannel && guide && (
          <div className="space-y-5">
            {guide.webhookManagement === "automatic" ? (
              /* Auto-managed (Telegram, Discord) */
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-6 w-6 text-green-500" />
                  <span className="text-base font-semibold">
                    Your {guide.name} bot is live!
                  </span>
                </div>
                <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Bot: <span className="font-medium text-foreground">{createdChannel.bot_name}</span>
                  </p>
                  {platform === "telegram" && telegramBotUsername && (
                    <p className="text-sm text-muted-foreground">
                      Send it a message right now:
                    </p>
                  )}
                </div>
                {platform === "telegram" && telegramBotUsername && (
                  <Button variant="outline" asChild>
                    <a
                      href={`https://t.me/${telegramBotUsername}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2"
                    >
                      Open in Telegram
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </Button>
                )}
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
                  </span>
                  Waiting for first message...
                </div>
              </div>
            ) : (
              /* Manual webhook (Slack, Teams, WhatsApp) */
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-6 w-6 text-green-500" />
                  <span className="text-base font-semibold">
                    Channel created -- one more step!
                  </span>
                </div>
                {createdChannel.webhook_url && (
                  <div className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      Paste this webhook URL in your {guide.name} settings:
                    </p>
                    <div className="flex items-center gap-2 rounded-lg border bg-muted/30 p-3">
                      <code className="flex-1 truncate text-xs">{createdChannel.webhook_url}</code>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0"
                        onClick={() => {
                          navigator.clipboard.writeText(createdChannel.webhook_url!);
                          toast.success("Webhook URL copied to clipboard");
                        }}
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                )}
                <Button variant="outline" size="sm" asChild>
                  <a
                    href={guide.externalUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2"
                  >
                    Open {guide.name} Dashboard
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </Button>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-yellow-400 opacity-75" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-yellow-500" />
                  </span>
                  Waiting for webhook verification...
                </div>
              </div>
            )}
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex items-center justify-between pt-2">
          {step < 3 ? (
            <>
              <Button
                variant="ghost"
                onClick={() => setStep((s) => Math.max(0, s - 1))}
                disabled={step === 0}
              >
                <ChevronLeft className="mr-1 h-4 w-4" />
                Back
              </Button>
              {step < 2 ? (
                <Button onClick={() => setStep((s) => s + 1)} disabled={!canProceed()}>
                  Next
                  <ChevronRight className="ml-1 h-4 w-4" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={!canProceed() || createChannel.isPending}
                >
                  {createChannel.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Create Channel
                </Button>
              )}
            </>
          ) : (
            <div className="flex w-full justify-end">
              <Button onClick={() => handleClose(false)}>
                Done
              </Button>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
