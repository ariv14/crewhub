import type { AgentStatus, VerificationLevel } from "@/types/agent";
import type { TaskStatus } from "@/types/task";

export const ROUTES = {
  home: "/",
  login: "/login",
  register: "/register",
  registerAgent: "/register-agent",

  // Marketplace
  teamMode: "/team",
  agents: "/agents",
  agentDetail: (id: string) => `/agents/${id}/`,
  category: (slug: string) => `/categories/${slug}/`,

  // User Dashboard
  dashboard: "/dashboard",
  myAgents: "/dashboard/agents",
  newAgent: "/dashboard/agents/new",
  agentSettings: (id: string) => `/dashboard/agents/${id}/`,
  myTasks: "/dashboard/tasks",
  taskDetail: (id: string) => `/dashboard/tasks/${id}/`,
  newTask: "/dashboard/tasks/new",
  retryTask: (agentId: string, skillId: string, message: string) =>
    `/dashboard/tasks/new?agent=${agentId}&skill=${encodeURIComponent(skillId)}&message=${encodeURIComponent(message)}`,
  team: "/dashboard/team",
  credits: "/dashboard/credits",
  settings: "/dashboard/settings",
  import: "/dashboard/import",

  // Admin
  admin: "/admin",
  adminAgents: "/admin/agents",
  adminAgentDetail: (id: string) => `/admin/agents/${id}/`,
  adminUsers: "/admin/users",
  adminTasks: "/admin/tasks",
  adminTransactions: "/admin/transactions",
  adminGovernance: "/admin/governance",
  adminHealth: "/admin/health",
  adminMcp: "/admin/mcp",
  adminSettings: "/admin/settings",
} as const;

export const TASK_STATUS_COLORS: Record<TaskStatus, string> = {
  submitted: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  pending_approval: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  pending_payment: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
  working: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  input_required: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  completed: "bg-green-500/15 text-green-400 border-green-500/30",
  failed: "bg-red-500/15 text-red-400 border-red-500/30",
  canceled: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
  rejected: "bg-red-500/15 text-red-400 border-red-500/30",
};

export const AGENT_STATUS_COLORS: Record<AgentStatus, string> = {
  active: "bg-green-500/15 text-green-400 border-green-500/30",
  inactive: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
  suspended: "bg-red-500/15 text-red-400 border-red-500/30",
};

export const VERIFICATION_COLORS: Record<VerificationLevel, string> = {
  unverified: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
  self_tested: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  namespace: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  quality: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  audit: "bg-green-500/15 text-green-400 border-green-500/30",
};

export const CATEGORIES = [
  { slug: "general", label: "General", icon: "Boxes" },
  { slug: "code", label: "Code & Dev", icon: "Code2" },
  { slug: "data", label: "Data & Analytics", icon: "BarChart3" },
  { slug: "writing", label: "Writing", icon: "PenTool" },
  { slug: "research", label: "Research", icon: "Search" },
  { slug: "design", label: "Design", icon: "Palette" },
  { slug: "automation", label: "Automation", icon: "Workflow" },
  { slug: "security", label: "Security", icon: "Shield" },
  { slug: "finance", label: "Finance", icon: "DollarSign" },
  { slug: "support", label: "Support", icon: "Headphones" },
] as const;

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
export const API_V1 = `${API_BASE_URL}/api/v1`;
