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
import { useMyWorkflows } from "@/lib/hooks/use-workflows";
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
  discord: { time: "~3 min", difficulty: "Easy", color: "text-green-500" },
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

  // Discord auto-setup state
  const [discordSetup, setDiscordSetup] = useState<{
    verified: boolean;
    loading: boolean;
    error: string | null;
    botUsername: string | null;
    applicationId: string | null;
    publicKey: string | null;
    inviteUrl: string | null;
    invited: boolean;
    endpointSet: boolean;
  }>({ verified: false, loading: false, error: null, botUsername: null, applicationId: null, publicKey: null, inviteUrl: null, invited: false, endpointSet: false });

  // Workflow state
  const [workflowId, setWorkflowId] = useState("");
  const [workflowMappings, setWorkflowMappings] = useState<Record<string, string>>({});

  // Fetch user's agents for step 3
  const { data: agentsData } = useAgents({
    owner_id: user?.id,
    per_page: 100,
  });
  const agents = agentsData?.agents ?? [];
  const selectedAgent = agents.find((a) => a.id === agentId);
  const skills = selectedAgent?.skills ?? [];

  // Fetch user's workflows for step 3
  const { data: workflowsData } = useMyWorkflows();
  const workflows = workflowsData?.workflows ?? [];

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
    setWorkflowId("");
    setWorkflowMappings({});
    setDiscordSetup({ verified: false, loading: false, error: null, botUsername: null, applicationId: null, publicKey: null, inviteUrl: null, invited: false, endpointSet: false });
  }

  function handleClose(open: boolean) {
    if (!open) reset();
    onOpenChange(open);
  }

  const guide = platform ? PLATFORM_GUIDES[platform] : null;

  // Discord: auto-setup from bot token
  async function handleDiscordVerify() {
    const token = credentials.bot_token?.trim();
    if (!token) return;
    setDiscordSetup((s) => ({ ...s, loading: true, error: null }));
    try {
      const isStaging = process.env.NEXT_PUBLIC_API_URL?.includes("staging");
      const gatewayBase = process.env.NEXT_PUBLIC_GATEWAY_URL
        || (isStaging ? "https://crewhub-gateway-staging.arimatch1.workers.dev" : "https://crewhub-gateway-production.arimatch1.workers.dev");
      const resp = await fetch(`${gatewayBase}/auto-setup-discord`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bot_token: token }),
      });
      const data = await resp.json();
      if (!resp.ok || !data.ok) {
        setDiscordSetup((s) => ({ ...s, loading: false, error: data.error || "Verification failed" }));
        return;
      }
      // Auto-populate credentials so they're sent to the backend
      setCredentials((prev) => ({
        ...prev,
        application_id: data.application_id,
        public_key: data.public_key,
      }));
      setDiscordSetup({
        verified: true,
        loading: false,
        error: null,
        botUsername: data.bot_username,
        applicationId: data.application_id,
        publicKey: data.public_key,
        inviteUrl: data.invite_url,
        invited: false,
        endpointSet: false,
      });
      if (!botName.trim()) {
        setBotName(data.bot_username || "Discord Bot");
      }
    } catch {
      setDiscordSetup((s) => ({ ...s, loading: false, error: "Network error — check your connection" }));
    }
  }

  // Validation per step
  function canProceed(): boolean {
    if (step === 0) return platform !== null;
    if (step === 1) {
      if (!guide) return false;
      if (!botName.trim()) return false;
      const allFilled = guide.credentials.every((c) => credentials[c.key]?.trim());
      if (!allFilled) return false;
      // Discord: must verify token + confirm bot invited
      if (platform === "discord" && (!discordSetup.verified || !discordSetup.invited)) return false;
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
        workflow_id: workflowId || undefined,
        workflow_mappings: Object.keys(workflowMappings).length > 0 ? workflowMappings : undefined,
        daily_credit_limit: dailyLimit || undefined,
        low_balance_threshold: lowBalance,
        pause_on_limit: pauseOnLimit,
        privacy_notice_url: privacyUrl.trim() || undefined,
      });
      setCreatedChannel(channel);

      // Auto-register webhook via CF Worker (browser has full DNS)
      if (platform === "telegram" && credentials.bot_token && channel.webhook_url) {
        try {
          const gatewayUrl = channel.webhook_url.split("/webhook/")[0];
          const resp = await fetch(`${gatewayUrl}/auto-register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              bot_token: credentials.bot_token,
              connection_id: channel.id,
            }),
          });
          const result = await resp.json();
          if (result.ok) {
            console.log("Telegram webhook registered:", result.webhook_url);
          } else {
            console.warn("Webhook registration failed:", result.error);
          }
        } catch (e) {
          console.warn("Auto webhook registration failed (non-blocking):", e);
        }
      }

      // Discord: register /ask slash command via CF Worker
      if (platform === "discord" && credentials.bot_token && channel.webhook_url) {
        try {
          const gatewayUrl = channel.webhook_url.split("/webhook/")[0];
          const resp = await fetch(`${gatewayUrl}/auto-register-discord`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              bot_token: credentials.bot_token,
              connection_id: channel.id,
            }),
          });
          const result = await resp.json();
          if (result.ok) {
            console.log("Discord slash command registered:", result.slash_command);
            if (result.endpoint_set) {
              console.log("Discord Interactions Endpoint URL set automatically");
              setDiscordSetup((s) => ({ ...s, endpointSet: true }));
            }
          } else {
            console.warn("Discord slash command registration failed:", result.error);
          }
        } catch (e) {
          console.warn("Discord auto-register failed (non-blocking):", e);
        }
      }

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
            {/* Setup instructions — platform-specific */}
            {platform === "discord" ? (
              /* Discord: rich guided setup */
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium">Create a Discord Bot</p>
                  <Button variant="outline" size="sm" asChild>
                    <a
                      href="https://discord.com/developers/applications"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2"
                    >
                      Open Developer Portal
                      <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                  </Button>
                </div>
                <div className="space-y-2">
                  {[
                    { num: "1", text: 'Click "New Application" and give it a name', hint: 'e.g. "My Support Bot"' },
                    { num: "2", text: 'Go to the Bot tab (left sidebar)', hint: null },
                    { num: "3", text: 'Click "Reset Token" and copy it', hint: "Save it now — you can't see it again!" },
                    { num: "4", text: 'Scroll down → enable "Message Content Intent"', hint: "Under Privileged Gateway Intents" },
                    { num: "5", text: 'Go to Installation tab → Guild Install → add "bot" scope', hint: 'Must have both "bot" and "applications.commands"' },
                  ].map((s) => (
                    <div key={s.num} className="flex gap-3 items-start">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">{s.num}</span>
                      <div>
                        <p className="text-sm text-foreground">{s.text}</p>
                        {s.hint && <p className="text-xs text-muted-foreground">{s.hint}</p>}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-xs text-blue-700 dark:text-blue-400">
                  Once you have the bot token, paste it below. We&apos;ll auto-detect your App ID, Public Key, and set up everything else.
                </div>
              </div>
            ) : (
              /* Other platforms: generic step list */
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
            )}

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
                          onChange={(e) => {
                            setCredentials((prev) => ({ ...prev, [cred.key]: e.target.value }));
                            // Reset Discord verification when token changes
                            if (platform === "discord" && cred.key === "bot_token" && discordSetup.verified) {
                              setDiscordSetup({ verified: false, loading: false, error: null, botUsername: null, applicationId: null, publicKey: null, inviteUrl: null, invited: false, endpointSet: false });
                            }
                          }}
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

            {/* Discord: Verify + Invite flow */}
            {platform === "discord" && (
              <div className="space-y-3">
                {!discordSetup.verified ? (
                  <>
                    <Button
                      onClick={handleDiscordVerify}
                      disabled={!credentials.bot_token?.trim() || credentials.bot_token.length < 50 || discordSetup.loading}
                      className="w-full"
                    >
                      {discordSetup.loading ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : null}
                      {discordSetup.loading ? "Verifying..." : "Verify Token"}
                    </Button>
                    {discordSetup.error && (
                      <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3">
                        <p className="text-xs text-red-600 dark:text-red-400">{discordSetup.error}</p>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="space-y-3">
                    {/* Verified success */}
                    <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-3 space-y-2">
                      <div className="flex items-center gap-2">
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                        <span className="text-sm font-medium">Token verified — bot: {discordSetup.botUsername}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        App ID and Public Key auto-detected.
                      </p>
                    </div>

                    {/* Invite button */}
                    <div className="space-y-2">
                      <p className="text-sm font-medium">Invite bot to your server</p>
                      <Button variant="outline" className="w-full" asChild>
                        <a
                          href={discordSetup.inviteUrl!}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={() => setDiscordSetup((s) => ({ ...s, invited: true }))}
                          className="inline-flex items-center gap-2"
                        >
                          <Gamepad2 className="h-4 w-4" />
                          Add Bot to Server
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      </Button>
                      {discordSetup.invited && (
                        <div className="flex items-center gap-2">
                          <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                          <span className="text-xs text-green-600 dark:text-green-400">
                            Bot invited — you can proceed
                          </span>
                        </div>
                      )}
                      {!discordSetup.invited && (
                        <div className="space-y-2">
                          <p className="text-xs text-muted-foreground">
                            Select a server you manage and click Authorize.
                          </p>
                          <details className="text-xs text-muted-foreground">
                            <summary className="cursor-pointer font-medium text-amber-600 dark:text-amber-400 hover:underline">
                              Getting &quot;Integration requires code grant&quot;?
                            </summary>
                            <div className="mt-2 space-y-1 pl-2 border-l-2 border-amber-500/30">
                              <p>Go to Discord Developer Portal → your app → <span className="font-medium text-foreground">Installation</span> tab.</p>
                              <p>Under <span className="font-medium text-foreground">Guild Install</span>, make sure both <code className="rounded bg-muted px-1">bot</code> and <code className="rounded bg-muted px-1">applications.commands</code> scopes are added.</p>
                              <p>Save and try the invite link again.</p>
                            </div>
                          </details>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

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

            {/* Workflow selection (optional) */}
            <div className="border-t pt-4 mt-4 space-y-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Workflow (for /workflow command)</p>
              <div className="space-y-2">
                <Label>Default Workflow</Label>
                <Select value={workflowId || "__none__"} onValueChange={(v) => setWorkflowId(v === "__none__" ? "" : v)}>
                  <SelectTrigger>
                    <SelectValue placeholder="None (disable /workflow)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__none__">None (disable /workflow)</SelectItem>
                    {workflows.map((wf) => (
                      <SelectItem key={wf.id} value={wf.id}>
                        {wf.name} ({wf.steps?.length || 0} steps)
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Users can trigger this workflow with <code className="rounded bg-muted px-1">/workflow</code> in Discord or <code className="rounded bg-muted px-1">!workflow</code> in Telegram/Slack.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Post-creation success screen */}
        {step === 3 && createdChannel && guide && (
          <div className="space-y-5">
            {guide.webhookManagement === "discord" ? (
              /* Discord: auto-setup or manual endpoint */
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-6 w-6 text-green-500" />
                  <span className="text-base font-semibold">
                    {discordSetup.endpointSet
                      ? "Your Discord bot is live!"
                      : "Almost done — one last step!"}
                  </span>
                </div>
                <div className="rounded-lg border bg-muted/30 p-4 space-y-2">
                  <p className="text-sm text-muted-foreground">
                    Bot: <span className="font-medium text-foreground">{createdChannel.bot_name}</span>
                  </p>
                  <p className="text-sm text-muted-foreground">
                    The <code className="rounded bg-muted px-1 py-0.5 text-xs">/ask</code> slash command has been registered automatically.
                  </p>
                  {discordSetup.endpointSet && (
                    <p className="text-sm text-muted-foreground">
                      Interactions Endpoint URL configured automatically.
                    </p>
                  )}
                </div>

                {/* Manual fallback: show endpoint URL if auto-set failed */}
                {!discordSetup.endpointSet && createdChannel.webhook_url && (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">
                      Paste this URL as your Interactions Endpoint URL:
                    </p>
                    <div className="flex items-center gap-2 rounded-lg border bg-muted/30 p-3">
                      <code className="flex-1 truncate text-xs">{createdChannel.webhook_url}</code>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7 shrink-0"
                        onClick={() => {
                          navigator.clipboard.writeText(createdChannel.webhook_url!);
                          toast.success("URL copied to clipboard");
                        }}
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                    <ol className="list-decimal space-y-1 pl-5 text-xs text-muted-foreground">
                      <li>Open your app in the Discord Developer Portal</li>
                      <li>Go to <span className="font-medium text-foreground">General Information</span></li>
                      <li>Paste the URL above into <span className="font-medium text-foreground">Interactions Endpoint URL</span></li>
                      <li>Click <span className="font-medium text-foreground">Save Changes</span></li>
                    </ol>
                    <Button variant="outline" size="sm" asChild>
                      <a
                        href={discordSetup.applicationId
                          ? `https://discord.com/developers/applications/${discordSetup.applicationId}/information`
                          : "https://discord.com/developers/applications"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-2"
                      >
                        Open App Settings
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    </Button>
                  </div>
                )}

                <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-3">
                  <p className="text-xs text-blue-700 dark:text-blue-400">
                    Use <code className="rounded bg-blue-500/10 px-1 py-0.5">/ask</code> in any channel where the bot is present. The slash command may take up to 1 hour to appear globally.
                  </p>
                </div>

                {discordSetup.endpointSet && (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span className="relative flex h-2.5 w-2.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                      <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
                    </span>
                    Waiting for first message...
                  </div>
                )}
              </div>
            ) : guide.webhookManagement === "automatic" ? (
              /* Auto-managed (Telegram) */
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
