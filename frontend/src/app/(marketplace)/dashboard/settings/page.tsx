"use client";

import { useState } from "react";
import { Copy, Key, Plus, Trash2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { createApiKey } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "sonner";

export default function SettingsPage() {
  const { user } = useAuth();
  const [apiKeyName, setApiKeyName] = useState("");
  const [generatedKey, setGeneratedKey] = useState("");
  const [generating, setGenerating] = useState(false);

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
        </TabsList>

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
              <p className="text-xs text-muted-foreground">
                Profile updates coming soon (requires backend PUT /auth/me).
              </p>
            </CardContent>
          </Card>
        </TabsContent>

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
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={copyKey}>
                      <Copy className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
