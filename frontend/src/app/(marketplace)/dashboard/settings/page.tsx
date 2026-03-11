"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Copy,
  Key,
  Plus,
  Trash2,
  Loader2,
  Eye,
  EyeOff,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { createApiKey, updateMe } from "@/lib/api/auth";
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

const PROVIDERS = [
  { id: "openai", name: "OpenAI", hint: "sk-..." },
  { id: "gemini", name: "Google Gemini", hint: "AI..." },
  { id: "anthropic", name: "Anthropic (Voyage)", hint: "pa-..." },
  { id: "cohere", name: "Cohere", hint: "..." },
  { id: "ollama", name: "Ollama", hint: "Local — no key needed" },
];

export default function SettingsPage() {
  const { user } = useAuth();

  // Spending limit state
  const [spendLimit, setSpendLimit] = useState("");
  const [savingLimit, setSavingLimit] = useState(false);

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

  // LLM Keys tab state
  const [llmKeys, setLlmKeys] = useState<LLMKeyInfo[]>([]);
  const [loadingKeys, setLoadingKeys] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState("");
  const [keyInput, setKeyInput] = useState("");
  const [showKeyInput, setShowKeyInput] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingProvider, setDeletingProvider] = useState<string | null>(null);

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

      <Tabs defaultValue="profile">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="api-keys">API Keys</TabsTrigger>
          <TabsTrigger value="llm-keys" className="gap-1.5">
            <Key className="h-3.5 w-3.5" />
            LLM Keys
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
                            onClick={() => handleDeleteKey(key.provider)}
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
      </Tabs>
    </div>
  );
}
