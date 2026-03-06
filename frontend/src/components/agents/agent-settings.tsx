"use client";

import { useState } from "react";
import { toast } from "sonner";
import { Loader2, RefreshCw, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  useAgent,
  useUpdateAgent,
  useDeleteAgent,
  useDeleteAgentPermanently,
  useDetectAgent,
} from "@/lib/hooks/use-agents";
import { useAuth } from "@/lib/auth-context";
import { ROUTES, CATEGORIES } from "@/lib/constants";
import type { AgentUpdate } from "@/types/agent";

export function AgentSettings({ agentId }: { agentId: string }) {
  const { user } = useAuth();
  const { data: agent, isLoading } = useAgent(agentId);
  const updateMutation = useUpdateAgent(agentId);
  const deleteMutation = useDeleteAgent();
  const hardDeleteMutation = useDeleteAgentPermanently();
  const detectMutation = useDetectAgent();

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("");
  const [category, setCategory] = useState("general");
  const [endpoint, setEndpoint] = useState("");
  const [initialized, setInitialized] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState("");

  // Initialize form from agent data
  if (agent && !initialized) {
    setName(agent.name);
    setDescription(agent.description);
    setVersion(agent.version);
    setCategory(agent.category);
    setEndpoint(agent.endpoint);
    setInitialized(true);
  }

  if (isLoading) {
    return (
      <div className="flex min-h-[200px] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!agent) {
    return <p className="text-muted-foreground">Agent not found.</p>;
  }

  if (user && agent.owner_id !== user.id) {
    return <p className="text-muted-foreground">You don&apos;t own this agent.</p>;
  }

  async function handleSave() {
    const data: AgentUpdate = {
      name,
      description,
      version,
      category,
      endpoint,
    };
    try {
      await updateMutation.mutateAsync(data);
      toast.success("Agent updated");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function handleRedetect() {
    if (!endpoint) return;
    try {
      const result = await detectMutation.mutateAsync(endpoint);
      setName(result.name);
      setDescription(result.description);
      setVersion(result.version || version);
      toast.success(
        `Re-detected: ${result.skills.length} skills, ${result.warnings.length} warnings`
      );
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Re-detect failed");
    }
  }

  async function handleDeactivate() {
    try {
      await deleteMutation.mutateAsync(agentId);
      toast.success("Agent deactivated");
      window.location.href = ROUTES.myAgents;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Deactivate failed");
    }
  }

  async function handleDelete() {
    try {
      await hardDeleteMutation.mutateAsync(agentId);
      toast.success("Agent deleted permanently");
      window.location.href = ROUTES.myAgents;
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Delete failed");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Agent Settings</h1>
        <p className="mt-1 text-muted-foreground">
          Manage <strong>{agent.name}</strong>
        </p>
      </div>

      {/* Details */}
      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
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
            <div className="space-y-2">
              <Label>Endpoint URL</Label>
              <Input
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>Skills</Label>
            <div className="flex flex-wrap gap-2">
              {agent.skills.map((s) => (
                <Badge key={s.id} variant="secondary">
                  {s.name}
                </Badge>
              ))}
            </div>
          </div>

          <Button onClick={handleSave} disabled={updateMutation.isPending}>
            {updateMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Save Changes
          </Button>
        </CardContent>
      </Card>

      {/* Re-detect */}
      <Card>
        <CardHeader>
          <CardTitle>Re-detect from Agent Card</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-muted-foreground">
            Re-fetch your agent&apos;s capabilities from the agent card. This
            will update the name, description, and skills.
          </p>
          <Button
            variant="outline"
            onClick={handleRedetect}
            disabled={detectMutation.isPending}
          >
            {detectMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Re-detect
          </Button>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded border border-destructive/20 p-4">
            <div>
              <p className="font-medium">Deactivate Agent</p>
              <p className="text-sm text-muted-foreground">
                Hides from marketplace. Existing tasks will complete.
              </p>
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  Deactivate
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Deactivate {agent.name}?</DialogTitle>
                  <DialogDescription>
                    This will hide the agent from the marketplace. Existing
                    tasks will still complete. You can reactivate later.
                  </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                  <Button variant="destructive" onClick={handleDeactivate}>
                    Deactivate
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="flex items-center justify-between rounded border border-destructive/20 p-4">
            <div>
              <p className="font-medium">Delete Agent</p>
              <p className="text-sm text-muted-foreground">
                Permanent. Type the agent name to confirm.
              </p>
            </div>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Delete {agent.name}?</DialogTitle>
                  <DialogDescription>
                    This action is permanent. Type{" "}
                    <strong>{agent.name}</strong> to confirm.
                  </DialogDescription>
                </DialogHeader>
                <Input
                  value={deleteConfirm}
                  onChange={(e) => setDeleteConfirm(e.target.value)}
                  placeholder={agent.name}
                />
                <DialogFooter>
                  <Button
                    variant="destructive"
                    disabled={deleteConfirm !== agent.name || hardDeleteMutation.isPending}
                    onClick={handleDelete}
                  >
                    {hardDeleteMutation.isPending ? (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    ) : null}
                    Delete Permanently
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
