"use client";

import { useState } from "react";
import { Key, Check, Loader2, Sparkles } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { setLLMKey } from "@/lib/api/llm-keys";
import { toast } from "sonner";

const QUICK_PROVIDERS = [
  {
    id: "openai",
    name: "OpenAI",
    placeholder: "sk-...",
    description: "GPT embeddings — most popular",
  },
  {
    id: "gemini",
    name: "Google Gemini",
    placeholder: "AI...",
    description: "Free tier available at ai.google.dev",
  },
];

export function StepApiKeys() {
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState<string | null>(null);

  async function handleSave(provider: string) {
    const key = values[provider];
    if (!key?.trim()) return;
    setSaving(provider);
    try {
      await setLLMKey(provider, key);
      setSaved((s) => ({ ...s, [provider]: true }));
      toast.success(`${provider} key saved`);
    } catch {
      toast.error(`Failed to save ${provider} key`);
    } finally {
      setSaving(null);
    }
  }

  const anySaved = Object.values(saved).some(Boolean);

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold">Set Up AI Keys</h2>
        <p className="mt-1 text-muted-foreground">
          CrewHub uses embeddings for smart agent discovery. Add an API key to
          enable semantic search — or skip and use keyword search.
        </p>
      </div>

      <div className="rounded-md border border-blue-500/20 bg-blue-500/5 px-4 py-3">
        <div className="flex items-start gap-2">
          <Sparkles className="mt-0.5 h-4 w-4 text-blue-500" />
          <div className="text-sm">
            <p className="font-medium text-blue-700 dark:text-blue-400">
              Free plan: 50 requests/day
            </p>
            <p className="text-muted-foreground">
              Works with any provider. Upgrade to Premium ($9/mo) later for
              unlimited.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-3">
        {QUICK_PROVIDERS.map((provider) => (
          <div
            key={provider.id}
            className="flex items-center gap-2 rounded-md border px-3 py-2.5"
          >
            <div className="min-w-0 flex-1 space-y-1">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">{provider.name}</Label>
                {saved[provider.id] && (
                  <Badge
                    variant="outline"
                    className="border-green-500/30 text-green-600"
                  >
                    <Check className="mr-1 h-3 w-3" />
                    Saved
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                {provider.description}
              </p>
              {!saved[provider.id] && (
                <div className="flex gap-2 pt-1">
                  <Input
                    type="password"
                    placeholder={provider.placeholder}
                    className="h-8 text-xs"
                    value={values[provider.id] ?? ""}
                    onChange={(e) =>
                      setValues((v) => ({ ...v, [provider.id]: e.target.value }))
                    }
                  />
                  <Button
                    size="sm"
                    className="h-8"
                    onClick={() => handleSave(provider.id)}
                    disabled={
                      saving === provider.id || !values[provider.id]?.trim()
                    }
                  >
                    {saving === provider.id ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <Key className="h-3.5 w-3.5" />
                    )}
                  </Button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <p className="text-center text-xs text-muted-foreground">
        {anySaved
          ? "Looking good! You can add more keys in Settings > LLM Keys."
          : "Skip — you can always add keys later in Settings."}
      </p>
    </div>
  );
}
