// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import {
  Server,
  Plus,
  Trash2,
  RefreshCw,
  Shield,
  Key,
  Globe,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  useMCPServers,
  useCreateMCPServer,
  useDeleteMCPServer,
  useRefreshTools,
  useMCPGrants,
  useRevokeMCPGrant,
  type MCPServer,
} from "@/lib/hooks/use-mcp";

function AddServerDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [description, setDescription] = useState("");
  const [authType, setAuthType] = useState("none");
  const [authToken, setAuthToken] = useState("");
  const createServer = useCreateMCPServer();

  function handleSubmit() {
    const authConfig: Record<string, string> = {};
    if (authType === "bearer" && authToken) authConfig.token = authToken;
    if (authType === "api_key" && authToken) authConfig.key = authToken;

    createServer.mutate(
      { name, url, description: description || undefined, auth_type: authType, auth_config: authConfig },
      {
        onSuccess: () => {
          setOpen(false);
          setName("");
          setUrl("");
          setDescription("");
          setAuthType("none");
          setAuthToken("");
        },
      },
    );
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Add MCP Server
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Register MCP Server</DialogTitle>
          <DialogDescription>
            Add an external MCP server so your agents can use its tools.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          <div className="space-y-1.5">
            <Label>Name</Label>
            <Input placeholder="e.g. My GitHub" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Server URL (HTTPS)</Label>
            <Input placeholder="https://mcp.example.com" value={url} onChange={(e) => setUrl(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Description (optional)</Label>
            <Input placeholder="What tools does this server provide?" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="space-y-1.5">
            <Label>Authentication</Label>
            <Select value={authType} onValueChange={setAuthType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None</SelectItem>
                <SelectItem value="bearer">Bearer Token</SelectItem>
                <SelectItem value="api_key">API Key</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {authType !== "none" && (
            <div className="space-y-1.5">
              <Label>{authType === "bearer" ? "Token" : "API Key"}</Label>
              <Input
                type="password"
                placeholder={authType === "bearer" ? "ghp_..." : "sk-..."}
                value={authToken}
                onChange={(e) => setAuthToken(e.target.value)}
              />
            </div>
          )}
          <Button onClick={handleSubmit} disabled={!name || !url || createServer.isPending} className="w-full">
            {createServer.isPending ? "Registering..." : "Register Server"}
          </Button>
          {createServer.isError && (
            <p className="text-xs text-destructive">{(createServer.error as Error).message}</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ServerCard({ server }: { server: MCPServer }) {
  const deleteServer = useDeleteMCPServer();
  const refreshTools = useRefreshTools();
  const tools = server.tools_cached?.tools || [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-primary" />
            <CardTitle className="text-base">{server.name}</CardTitle>
          </div>
          <div className="flex gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              onClick={() => refreshTools.mutate(server.id)}
              disabled={refreshTools.isPending}
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshTools.isPending ? "animate-spin" : ""}`} />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-destructive hover:text-destructive"
              onClick={() => deleteServer.mutate(server.id)}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
        {server.description && (
          <CardDescription className="text-xs">{server.description}</CardDescription>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap gap-1.5">
          <Badge variant="outline" className="text-[10px]">
            {server.auth_type === "none" ? (
              <><Globe className="mr-1 h-2.5 w-2.5" />Public</>
            ) : (
              <><Key className="mr-1 h-2.5 w-2.5" />{server.auth_type}</>
            )}
          </Badge>
          {server.is_public && (
            <Badge variant="outline" className="text-[10px]">
              <Shield className="mr-1 h-2.5 w-2.5" />Shared
            </Badge>
          )}
        </div>
        <div className="text-xs text-muted-foreground truncate" title={server.url}>
          {server.url}
        </div>
        {tools.length > 0 && (
          <div className="space-y-1">
            <div className="flex items-center gap-1 text-xs font-medium">
              <Wrench className="h-3 w-3" />
              {tools.length} tool{tools.length !== 1 ? "s" : ""}
            </div>
            <div className="flex flex-wrap gap-1">
              {tools.slice(0, 8).map((t) => (
                <Badge key={t.name} variant="secondary" className="text-[10px]">
                  {t.name}
                </Badge>
              ))}
              {tools.length > 8 && (
                <Badge variant="secondary" className="text-[10px]">
                  +{tools.length - 8} more
                </Badge>
              )}
            </div>
          </div>
        )}
        {tools.length === 0 && (
          <p className="text-xs text-muted-foreground">
            No tools cached. Click refresh to discover tools.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function MCPPage() {
  const { data: servers, isLoading: serversLoading } = useMCPServers();
  const { data: grants, isLoading: grantsLoading } = useMCPGrants();
  const revokeGrant = useRevokeMCPGrant();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">MCP Servers</h1>
          <p className="text-sm text-muted-foreground">
            Connect external tools to your AI agents via the Model Context Protocol.
          </p>
        </div>
        <AddServerDialog />
      </div>

      {/* Servers Grid */}
      {serversLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-3">
                <div className="h-5 w-32 rounded bg-muted" />
              </CardHeader>
              <CardContent>
                <div className="h-4 w-full rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : servers && servers.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {servers.map((s) => (
            <ServerCard key={s.id} server={s} />
          ))}
        </div>
      ) : (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Server className="mb-3 h-10 w-10 text-muted-foreground/50" />
            <h3 className="text-sm font-medium">No MCP servers registered</h3>
            <p className="mt-1 text-xs text-muted-foreground max-w-sm">
              Register an MCP server to give your agents access to external tools like
              GitHub, databases, Google Drive, and more.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Grants Section */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Agent Access Grants</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Control which agents can access which MCP servers.
        </p>
        {grantsLoading ? (
          <div className="h-20 animate-pulse rounded-lg bg-muted" />
        ) : grants && grants.length > 0 ? (
          <div className="rounded-lg border">
            <div className="grid grid-cols-4 gap-4 border-b p-3 text-xs font-medium text-muted-foreground">
              <span>Server</span>
              <span>Agent</span>
              <span>Scopes</span>
              <span />
            </div>
            {grants.map((g) => (
              <div key={g.id} className="grid grid-cols-4 gap-4 border-b p-3 text-sm last:border-0">
                <span className="truncate">{g.server_name || g.mcp_server_id.slice(0, 8)}</span>
                <span className="truncate text-muted-foreground">{g.agent_id.slice(0, 8)}...</span>
                <span className="text-xs text-muted-foreground">
                  {g.scopes.length > 0 ? g.scopes.join(", ") : "All tools"}
                </span>
                <div className="flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-xs text-destructive hover:text-destructive"
                    onClick={() => revokeGrant.mutate(g.id)}
                  >
                    Revoke
                  </Button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-8 text-center">
              <Shield className="mb-2 h-8 w-8 text-muted-foreground/50" />
              <p className="text-xs text-muted-foreground">
                No grants yet. Grant agents access to MCP servers from the agent detail page.
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
