// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import {
  Copy,
  Key,
  Plus,
  Trash2,
  Loader2,
  Eye,
  EyeOff,
  Sparkles,
  ExternalLink,
  CheckCircle2,
  XCircle,
  ChevronDown,
  Radio,
  Cookie,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api-client";
import { API_V1 } from "@/lib/constants";
import { createApiKey, revokeApiKey, updateMe } from "@/lib/api/auth";
import { listLLMKeys, setLLMKey, deleteLLMKey } from "@/lib/api/llm-keys";
import type { LLMKeyInfo } from "@/lib/api/llm-keys";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { ChannelsTab } from "./channels-tab";
import { resetAnalyticsConsent } from "@/components/shared/posthog-provider";

const PROVIDERS = [
  { id: "openai", name: "OpenAI", hint: "sk-..." },
  { id: "gemini", name: "Google Gemini", hint: "AI..." },
  { id: "anthropic", name: "Anthropic (Voyage)", hint: "pa-..." },
  { id: "cohere", name: "Cohere", hint: "..." },
  { id: "ollama", name: "Ollama", hint: "Local — no key needed" },
];

const VALID_TABS = ["profile", "api-keys", "builder", "llm-keys", "channels"];

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const searchParams = useSearchParams();
  const initialTab = useMemo(() => {
    const tab = searchParams.get("tab");
    return tab && VALID_TABS.includes(tab) ? tab : "profile";
  }, [searchParams]);
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;

  // Spending limit state
  const [spendLimit, setSpendLimit] = useState("");
  const [savingLimit, setSavingLimit] = useState(false);

  // Cookie consent state
  const [cookieConsent, setCookieConsent] = useState<string | null>(() =>
    typeof window !== "undefined" ? localStorage.getItem("analytics_consent") : null
  );

  // GDPR: export + delete account state
  const [exporting, setExporting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleting, setDeleting] = useState(false);

  async function handleExportData() {
    setExporting(true);
    try {
      const res = await fetch(`${API_V1}/auth/me/export`, {
        headers: token ? (token.startsWith("a2a_") ? { "X-API-Key": token } : { Authorization: `Bearer ${token}` }) : {},
      });
      if (!res.ok) throw new Error("Export failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `crewhub-export-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("Data exported");
    } catch {
      toast.error("Export failed — try again later");
    } finally {
      setExporting(false);
    }
  }

  async function handleDeleteAccount() {
    setDeleting(true);
    try {
      await api.delete("/auth/me", { confirmation: "DELETE" });
      toast.success("Account deleted");
      logout();
      window.location.href = "/";
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Deletion failed");
    } finally {
      setDeleting(false);
    }
  }

  useEffect(() => {
    if (user?.daily_spend_limit != null) {
      setSpendLimit(String(user.daily_spend_limit));
    }
  }, [user?.daily_spend_limit]);

  async function handleSaveSpendLimit() {
    setSavingLimit(true);
    try {
      const val = spendLimit.trim() ? parseFloat(spendLimit) : null;
      await updateMe({ daily_spend_limit: val && val > 0 ? val : null });
      toast.success(val ? `Daily spend limit set to ${val} credits` : "Daily spend limit removed");
    } catch {
      toast.error("Failed to save spending limit");
    } finally {
      setSavingLimit(false);
    }
  }

  // API Keys tab state
  const [apiKeyName, setApiKeyName] = useState("");
  const [generatedKey, setGeneratedKey] = useState("");
  const [generating, setGenerating] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [showRevokeConfirm, setShowRevokeConfirm] = useState(false);

  // LLM Keys tab state
  const [llmKeys, setLlmKeys] = useState<LLMKeyInfo[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingProvider, setDeletingProvider] = useState<string | null>(null);
  const [confirmDeleteProvider, setConfirmDeleteProvider] = useState<string | null>(null);

  const loadLLMKeys = useCallback(async () => {
    setLoadingKeys(true);
    try {
      const data = await listLLMKeys();
      setLlmKeys(data.keys);
    } catch {
      // silently fail — keys tab will show empty state
    } finally {
      setLoadingKeys(false);
    }
  }, []);

  useEffect(() => {
    loadLLMKeys();
  }, [loadLLMKeys]);

  // API Key handlers
  async function handleGenerateKey() {
    if (!apiKeyName.trim()) return;
    setGenerating(true);
    try {
      const result = await createApiKey({ name: apiKeyName });
      setGeneratedKey(result.key);
      setApiKeyName("");
      toast.success("API key generated");
    } catch {
      toast.error("Failed to generate API key");
    } finally {
      setGenerating(false);
    }
  }

  async function copyKey() {
    await navigator.clipboard.writeText(generatedKey);
    toast.success("Copied to clipboard");
  }

  async function handleRevokeKey() {
    setRevoking(true);
    try {
      await revokeApiKey();
      setGeneratedKey("");
      setShowRevokeConfirm(false);
      toast.success("API key revoked");
    } catch {
      toast.error("Failed to revoke API key");
    } finally {
      setRevoking(false);
    }
  }

  // LLM Key handlers
  async function handleSaveKey() {
    if (!selectedProvider || !keyInput.trim()) return;
    setSaving(true);
    try {
      await setLLMKey(selectedProvider, keyInput);
      toast.success(`${selectedProvider} key saved`);
      setKeyInput("");
      setSelectedProvider("");
      await loadLLMKeys();
    } catch {
      toast.error("Failed to save key");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteKey(provider: string) {
    setDeletingProvider(provider);
    try {
      await deleteLLMKey(provider);
      toast.success(`${provider} key removed`);
      await loadLLMKeys();
    } catch {
      toast.error("Failed to remove key");
    } finally {
      setDeletingProvider(null);
    }
  }

  const configuredKeys = llmKeys.filter((k) => k.is_set);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Manage your profile, API keys, and LLM keys
        </p>
      </div>

      <Tabs defaultValue={initialTab}>
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="builder" className="gap-1.5">
            <Sparkles className="h-3.5 w-3.5" />
            Builder
          </TabsTrigger>
          <TabsTrigger value="llm-keys" className="gap-1.5">
            <Key className="h-3.5 w-3.5" />
            LLM Keys
          </TabsTrigger>
          <TabsTrigger value="channels" className="gap-1.5">
            <Radio className="h-3.5 w-3.5" />
            Channels
          </TabsTrigger>
        </TabsList>

        {/* ── Profile Tab ── */}
        <TabsContent value="profile" className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Profile Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={user?.name ?? ""} disabled />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={user?.email ?? ""} disabled />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Spending Limit</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Set a daily credit spending limit to prevent accidental overuse.
                Leave empty for unlimited.
              </p>
              <div className="flex gap-2">
                <Input
                  type="number"
                  min="0"
                  step="10"
                  placeholder="No limit"
                  value={spendLimit}
                  onChange={(e) => setSpendLimit(e.target.value)}
                  className="max-w-[200px]"
                />
                <Button onClick={handleSaveSpendLimit} disabled={savingLimit}>
                  {savingLimit ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : null}
                  Save
                </Button>
              </div>
              {user?.daily_spend_limit != null && user.daily_spend_limit > 0 && (
                <p className="text-xs text-muted-foreground">
                  Current limit: {user.daily_spend_limit} credits/day
                </p>
              )}
            </CardContent>
          </Card>

          {/* Cookie Preferences */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Cookie className="h-4 w-4" />
                Cookie Preferences
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  <span className="font-medium text-foreground">Analytics cookies</span> help us understand
                  how people use CrewHub — which pages are popular, where users get stuck, and how we
                  can improve. No personally identifiable form data is captured.
                </p>
                <p className="text-sm text-muted-foreground">
                  <span className="font-medium text-foreground">Essential cookies</span> keep you signed in
                  and are required for the platform to work. These cannot be turned off.
                </p>
              </div>
              <div className="flex items-center justify-between rounded-md border px-3 py-2.5">
                <div>
                  <p className="text-sm font-medium">Analytics Cookies</p>
                  <p className="text-xs text-muted-foreground">
                    {cookieConsent === "true"
                      ? "Enabled — helping us improve CrewHub"
                      : cookieConsent === "false"
                        ? "Disabled — no analytics data collected"
                        : "No preference set"}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    resetAnalyticsConsent();
                    setCookieConsent(null);
                    toast.success("Preferences reset — consent banner will reappear");
                  }}
                >
                  Reset Preferences
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                For full details on what we collect, how long it&apos;s stored, and our data practices,
                see our{" "}
                <a href="/privacy" className="text-primary hover:underline">Privacy Policy</a>.
              </p>
            </CardContent>
          </Card>

          {/* Data & Account — Danger Zone */}
          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle className="text-base text-destructive">Data &amp; Account</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">Download Your Data</p>
                  <p className="text-xs text-muted-foreground">Export all your data as JSON (GDPR Article 20)</p>
                </div>
                <Button variant="outline" size="sm" onClick={handleExportData} disabled={exporting}>
                  {exporting ? "Exporting..." : "Download"}
                </Button>
              </div>
              <div className="border-t pt-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">Delete Account</p>
                    <p className="text-xs text-muted-foreground">Permanently delete your account and all data</p>
                  </div>
                  <Button variant="destructive" size="sm" onClick={() => setShowDeleteDialog(true)}>
                    Delete Account
                  </Button>
                </div>
              </div>
              {showDeleteDialog && (
                <div className="rounded-lg border border-destructive/50 bg-destructive/5 p-4 space-y-3">
                  <p className="text-sm text-destructive font-medium">This action cannot be undone.</p>
                  <p className="text-xs text-muted-foreground">Your personal data will be scrubbed immediately. Agents and workflows will be deleted. Transaction records are retained for financial compliance.</p>
                  <Input
                    placeholder='Type "DELETE" to confirm'
                    value={deleteConfirmText}
                    onChange={(e) => setDeleteConfirmText(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <Button
                      variant="destructive"
                      size="sm"
                      disabled={deleteConfirmText !== "DELETE" || deleting}
                      onClick={handleDeleteAccount}
                    >
                      {deleting ? "Deleting..." : "Permanently Delete"}
                    </Button>
                    <Button variant="outline" size="sm" onClick={() => { setShowDeleteDialog(false); setDeleteConfirmText(""); }}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── API Keys Tab ── */}
        <TabsContent value="api-keys" className="mt-6 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Generate API Key</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  placeholder="Key name (e.g., my-agent)"
                  value={apiKeyName}
                  onChange={(e) => setApiKeyName(e.target.value)}
                />
                <Button onClick={handleGenerateKey} disabled={generating}>
                  <Plus className="mr-2 h-4 w-4" />
                  Generate
                </Button>
              </div>
              {generatedKey && (
                <div className="mt-4 rounded-md border bg-muted/30 p-3">
                  <p className="mb-1 text-xs text-muted-foreground">
                    Copy this key now — it won&apos;t be shown again
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs">{generatedKey}</code>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={copyKey}
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Revoke API Key</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="mb-3 text-sm text-muted-foreground">
                Revoke your current API key. Any integrations using this key will stop working.
              </p>
              {showRevokeConfirm ? (
                <div className="flex items-center gap-2">
                  <p className="text-sm text-destructive">Are you sure?</p>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleRevokeKey}
                    disabled={revoking}
                  >
                    {revoking && <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />}
                    Yes, Revoke
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowRevokeConfirm(false)}
                  >
                    Cancel
                  </Button>
                </div>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowRevokeConfirm(true)}
                  className="text-destructive hover:text-destructive"
                >
                  <Trash2 className="mr-2 h-3.5 w-3.5" />
                  Revoke Key
                </Button>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── LLM Keys Tab ── */}
        <TabsContent value="llm-keys" className="mt-6 space-y-4">
          {/* Configured Keys */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Your API Keys</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingKeys ? (
                <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading keys...
                </div>
              ) : configuredKeys.length === 0 ? (
                <p className="py-4 text-sm text-muted-foreground">
                  No API keys configured yet. Add one below to enable semantic
                  search and embeddings.
                </p>
              ) : (
                <div className="space-y-2">
                  {llmKeys
                    .filter((k) => k.provider !== "ollama")
                    .map((key) => (
                      <div
                        key={key.provider}
                        className="flex items-center justify-between rounded-md border px-3 py-2"
                      >
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium capitalize">
                            {PROVIDERS.find((p) => p.id === key.provider)?.name ??
                              key.provider}
                          </span>
                          {key.is_set ? (
                            <Badge
                              variant="outline"
                              className="border-green-500/30 text-green-600"
                            >
                              Configured
                            </Badge>
                          ) : (
                            <Badge variant="secondary">Not set</Badge>
                          )}
                          {key.masked_key && (
                            <code className="text-xs text-muted-foreground">
                              {key.masked_key}
                            </code>
                          )}
                        </div>
                        {key.is_set && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                            onClick={() => setConfirmDeleteProvider(key.provider)}
                            disabled={deletingProvider === key.provider}
                          >
                            {deletingProvider === key.provider ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Trash2 className="h-3.5 w-3.5" />
                            )}
                          </Button>
                        )}
                      </div>
                    ))}
                </div>
              )}

              <Separator className="my-4" />

              {/* Add/Update Key Form */}
              <div className="space-y-3">
                <Label>Add or Update a Key</Label>
                <div className="flex gap-2">
                  <Select
                    value={selectedProvider}
                    onValueChange={setSelectedProvider}
                  >
                    <SelectTrigger className="w-[200px]">
                      <SelectValue placeholder="Provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {PROVIDERS.filter((p) => p.id !== "ollama").map((p) => (
                        <SelectItem key={p.id} value={p.id}>
                          {p.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="relative flex-1">
                    <Input
                      type={showKeyInput ? "text" : "password"}
                      placeholder={
                        PROVIDERS.find((p) => p.id === selectedProvider)?.hint ??
                        "Paste your API key"
                      }
                      value={keyInput}
                      onChange={(e) => setKeyInput(e.target.value)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
                      onClick={() => setShowKeyInput(!showKeyInput)}
                    >
                      {showKeyInput ? (
                        <EyeOff className="h-3.5 w-3.5" />
                      ) : (
                        <Eye className="h-3.5 w-3.5" />
                      )}
                    </Button>
                  </div>
                  <Button
                    onClick={handleSaveKey}
                    disabled={saving || !selectedProvider || !keyInput.trim()}
                  >
                    {saving ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : (
                      <Key className="mr-2 h-4 w-4" />
                    )}
                    Save
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Keys are encrypted at rest. Ollama runs locally and needs no
                  key.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
        {/* Builder Settings Tab */}
        <TabsContent value="builder" className="mt-6 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-primary" />
                Agent Builder Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Free Tier Info */}
              <div className="rounded-lg border border-primary/20 bg-primary/5 p-4">
                <p className="text-sm font-medium">Free Trial</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  You get 3 free agent builds. Agents run on CrewHub&apos;s infrastructure
                  using our default LLM. Optionally bring your own LLM key for custom models.
                </p>
              </div>

              {/* LLM Provider for Builder */}
              <div className="space-y-3">
                <Label className="text-sm font-semibold">LLM Provider (Optional)</Label>
                <p className="text-xs text-muted-foreground">
                  Bring your own key for faster or premium model responses.
                  Leave blank to use CrewHub&apos;s default (Groq Llama 3.3 70B — free).
                </p>

                {/* Provider Guides */}
                <div className="space-y-2">
                  {[
                    {
                      name: "Groq (Free — Recommended)",
                      prefix: "gsk_",
                      steps: [
                        "Go to console.groq.com",
                        "Sign up (free, no credit card)",
                        'Click "API Keys" → "Create API Key"',
                        'Name: "CrewHub", copy key (starts with gsk_)',
                      ],
                      link: "https://console.groq.com",
                      linkLabel: "Open Groq Console",
                      model: "Llama 3.3 70B | Free: 30 req/min",
                    },
                    {
                      name: "OpenAI",
                      prefix: "sk-",
                      steps: [
                        "Go to platform.openai.com/api-keys",
                        "Sign in or create account",
                        '"Create new secret key" → name "CrewHub"',
                        "Copy key (starts with sk-)",
                      ],
                      link: "https://platform.openai.com/api-keys",
                      linkLabel: "Open OpenAI Platform",
                      model: "GPT-4o ($2.50/1M tokens), GPT-4o-mini ($0.15/1M)",
                    },
                    {
                      name: "Anthropic",
                      prefix: "sk-ant-",
                      steps: [
                        "Go to console.anthropic.com",
                        "Settings → API Keys",
                        '"Create Key" → name "CrewHub"',
                        "Copy key (starts with sk-ant-)",
                      ],
                      link: "https://console.anthropic.com",
                      linkLabel: "Open Anthropic Console",
                      model: "Claude Sonnet 4 ($3/1M), Haiku ($0.25/1M)",
                    },
                    {
                      name: "Google Gemini",
                      prefix: "",
                      steps: [
                        "Go to aistudio.google.com/apikey",
                        "Sign in with Google account",
                        '"Create API Key" → select project',
                        "Copy key",
                      ],
                      link: "https://aistudio.google.com/apikey",
                      linkLabel: "Open Google AI Studio",
                      model: "Gemini 2.0 Flash (free tier), Pro ($1.25/1M)",
                    },
                  ].map((provider) => (
                    <details
                      key={provider.name}
                      className="rounded-lg border bg-card"
                    >
                      <summary className="flex cursor-pointer items-center justify-between px-4 py-2.5 text-sm font-medium hover:bg-accent/50">
                        {provider.name}
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      </summary>
                      <div className="border-t px-4 py-3 text-xs text-muted-foreground">
                        <ol className="mb-2 list-decimal space-y-1 pl-4">
                          {provider.steps.map((step, i) => (
                            <li key={i}>{step}</li>
                          ))}
                        </ol>
                        <p className="mb-2 text-[10px]">
                          Model: {provider.model}
                        </p>
                        <a
                          href={provider.link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-primary hover:underline"
                        >
                          {provider.linkLabel}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </div>
                    </details>
                  ))}
                </div>
              </div>

              <Separator />

              {/* Paid Tier — HuggingFace Key */}
              <div className="space-y-3">
                <Label className="text-sm font-semibold">
                  HuggingFace API Key
                  <Badge variant="outline" className="ml-2 text-[10px]">Paid Tier</Badge>
                </Label>
                <p className="text-xs text-muted-foreground">
                  Required for the paid Builder tier ($5/mo). Your agents deploy to your
                  own HuggingFace account for full isolation. CrewHub manages everything.
                </p>
                <details className="rounded-lg border bg-card">
                  <summary className="flex cursor-pointer items-center justify-between px-4 py-2.5 text-sm font-medium hover:bg-accent/50">
                    How to get your HuggingFace key
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  </summary>
                  <div className="border-t px-4 py-3 text-xs text-muted-foreground">
                    <ol className="mb-2 list-decimal space-y-1 pl-4">
                      <li>Go to huggingface.co/settings/tokens</li>
                      <li>Click &quot;New token&quot;</li>
                      <li>Name: &quot;CrewHub Builder&quot;</li>
                      <li>Role: select <strong>Write</strong> (required to create Spaces)</li>
                      <li>Click &quot;Generate&quot;, copy the key (starts with hf_)</li>
                    </ol>
                    <div className="flex gap-3">
                      <a
                        href="https://huggingface.co/join"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        Create HF Account
                        <ExternalLink className="h-3 w-3" />
                      </a>
                      <a
                        href="https://huggingface.co/settings/tokens"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-primary hover:underline"
                      >
                        Get Token
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                  </div>
                </details>
                <p className="text-[10px] text-muted-foreground/70">
                  Your keys are encrypted at rest. CrewHub uses them only to create and
                  manage Spaces in your account. You can revoke anytime on HuggingFace.
                </p>
              </div>

              {/* Coming Soon */}
              <div className="rounded-lg border border-dashed border-muted-foreground/20 p-4 text-center">
                <p className="text-sm font-medium text-muted-foreground">
                  Paid Builder tier coming soon
                </p>
                <p className="mt-1 text-xs text-muted-foreground/70">
                  $5/mo for 20 agents on your own HuggingFace infrastructure.
                  Free trial: 3 agents on CrewHub&apos;s pool.
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Channels Tab ── */}
        <TabsContent value="channels" className="mt-6">
          <ChannelsTab />
        </TabsContent>

      </Tabs>
      <ConfirmDialog
        open={!!confirmDeleteProvider}
        onOpenChange={(open) => { if (!open) setConfirmDeleteProvider(null); }}
        title="Remove API Key"
        description={`Are you sure you want to remove the ${PROVIDERS.find((p) => p.id === confirmDeleteProvider)?.name ?? confirmDeleteProvider} API key? This action cannot be undone.`}
        confirmLabel="Remove"
        variant="destructive"
        onConfirm={() => {
          if (confirmDeleteProvider) {
            handleDeleteKey(confirmDeleteProvider);
            setConfirmDeleteProvider(null);
          }
        }}
        loading={!!deletingProvider}
      />
    </div>
  );
}
