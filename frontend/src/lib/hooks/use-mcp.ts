// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "../auth-context";
import { API_V1 } from "../constants";
import { getAuthHeaders } from "../auth-headers";

async function fetchJson(path: string, options?: RequestInit) {
  const token = typeof window !== "undefined" ? localStorage.getItem("auth_token") : null;
  if (!token) throw new Error("Not authenticated");
  const res = await fetch(`${API_V1}${path}`, {
    ...options,
    headers: { ...getAuthHeaders(token), "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return null;
  return res.json();
}

// --- MCP Servers ---

export interface MCPServer {
  id: string;
  owner_id: string;
  name: string;
  url: string;
  description: string | null;
  auth_type: string;
  tools_cached: { tools?: { name: string; description?: string }[] } | null;
  is_public: boolean;
  status: string;
  created_at: string;
  updated_at: string;
}

export function useMCPServers() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["mcp-servers"],
    queryFn: () => fetchJson("/mcp-servers/").then((d) => d.servers as MCPServer[]),
    enabled: !!user,
  });
}

export function useCreateMCPServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; url: string; description?: string; auth_type?: string; auth_config?: Record<string, string>; is_public?: boolean }) =>
      fetchJson("/mcp-servers/", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mcp-servers"] }),
  });
}

export function useDeleteMCPServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => fetchJson(`/mcp-servers/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mcp-servers"] }),
  });
}

export function useRefreshTools() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => fetchJson(`/mcp-servers/${id}/refresh-tools`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mcp-servers"] }),
  });
}

// --- MCP Grants ---

export interface MCPGrant {
  id: string;
  user_id: string;
  agent_id: string;
  mcp_server_id: string;
  scopes: string[];
  expires_at: string | null;
  created_at: string;
  server_name: string | null;
}

export function useMCPGrants() {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["mcp-grants"],
    queryFn: () => fetchJson("/mcp-servers/grants/").then((d) => d.grants as MCPGrant[]),
    enabled: !!user,
  });
}

export function useCreateMCPGrant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { agent_id: string; mcp_server_id: string; scopes?: string[] }) =>
      fetchJson("/mcp-servers/grants/", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mcp-grants"] }),
  });
}

export function useRevokeMCPGrant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => fetchJson(`/mcp-servers/grants/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["mcp-grants"] }),
  });
}
