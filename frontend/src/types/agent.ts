export type AgentStatus = "active" | "inactive" | "suspended";
export type VerificationLevel = "unverified" | "self_tested" | "namespace" | "quality" | "audit";
export type LicenseType = "open" | "freemium" | "commercial" | "subscription" | "trial";
export type BillingModel = "per_task" | "per_token" | "per_minute" | "tiered";

export interface UsageQuota {
  daily_tasks: number | null;
  monthly_tasks: number | null;
  max_tokens_per_task: number | null;
  rate_limit_rpm: number | null;
}

export interface PricingTier {
  name: string;
  billing_model: BillingModel;
  credits_per_unit: number;
  monthly_fee: number;
  quota: UsageQuota | null;
  features: string[];
  is_default: boolean;
}

export interface PricingModel {
  license_type: LicenseType;
  tiers: PricingTier[];
  model: string;
  credits: number;
  trial_days: number | null;
  trial_task_limit: number | null;
}

export interface SLADefinition {
  max_latency_ms: number | null;
  uptime_guarantee: number | null;
}

export interface SkillExample {
  input: string;
  output: string;
  description: string | null;
}

export interface Skill {
  id: string;
  skill_key: string;
  name: string;
  description: string;
  input_modes: string[];
  output_modes: string[];
  examples: SkillExample[];
  avg_credits: number;
  avg_latency_ms: number;
}

export interface SkillCreate {
  skill_key: string;
  name: string;
  description: string;
  input_modes: string[];
  output_modes: string[];
  examples: SkillExample[];
  avg_credits: number;
  avg_latency_ms: number;
}

export interface EmbeddingConfig {
  provider: string;
  model: string;
}

export interface Agent {
  id: string;
  owner_id: string;
  name: string;
  description: string;
  version: string;
  endpoint: string;
  capabilities: Record<string, unknown>;
  skills: Skill[];
  security_schemes: Record<string, unknown>[];
  category: string;
  tags: string[];
  pricing: PricingModel;
  license_type: LicenseType;
  sla: SLADefinition | null;
  embedding_config: EmbeddingConfig | null;
  accepted_payment_methods: string[];
  mcp_server_url: string | null;
  avatar_url: string | null;
  conversation_starters: string[];
  test_cases: Record<string, unknown>[];
  did: string | null;
  status: AgentStatus;
  verification_level: VerificationLevel;
  reputation_score: number;
  total_tasks_completed: number;
  success_rate: number;
  avg_latency_ms: number;
  created_at: string;
  updated_at: string;
}

export interface AgentCreate {
  name: string;
  description: string;
  version: string;
  endpoint: string;
  capabilities: Record<string, unknown>;
  skills: SkillCreate[];
  security_schemes: Record<string, unknown>[];
  category: string;
  tags: string[];
  pricing: PricingModel;
  sla?: SLADefinition;
  embedding_config?: EmbeddingConfig;
  accepted_payment_methods: string[];
  mcp_server_url?: string;
  avatar_url?: string;
  conversation_starters?: string[];
  test_cases?: Record<string, unknown>[];
}

export interface AgentUpdate extends Partial<AgentCreate> {}

export interface AgentListResponse {
  agents: Agent[];
  total: number;
  page: number;
  per_page: number;
}

export interface DetectedSkill {
  skill_key: string;
  name: string;
  description: string;
  input_modes: string[];
  output_modes: string[];
}

export interface DetectResponse {
  name: string;
  description: string;
  url: string;
  version: string;
  capabilities: Record<string, unknown>;
  skills: DetectedSkill[];
  suggested_registration: AgentCreate;
  card_url: string;
  warnings: string[];
}

export interface AgentCardResponse {
  name: string;
  description: string;
  url: string;
  version: string;
  capabilities: Record<string, unknown>;
  skills: Record<string, unknown>[];
  securitySchemes: Record<string, unknown>[];
  defaultInputModes: string[];
  defaultOutputModes: string[];
}
