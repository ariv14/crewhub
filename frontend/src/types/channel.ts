// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.

export type ChannelPlatform = "telegram" | "slack" | "discord" | "teams" | "whatsapp";
export type ChannelStatus = "active" | "paused" | "disconnected" | "pending";

export interface Channel {
  id: string;
  owner_id: string;
  platform: ChannelPlatform;
  bot_name: string;
  agent_id: string;
  agent_name?: string;
  skill_id?: string;
  workflow_id?: string;
  workflow_name?: string;
  status: ChannelStatus;
  paused_reason?: string;
  daily_credit_limit?: number;
  low_balance_threshold: number;
  pause_on_limit: boolean;
  webhook_url?: string;
  error_message?: string;
  last_active_at?: string;
  messages_today: number;
  credits_used_today: number;
  total_messages?: number;
  total_credits?: number;
  created_at: string;
  updated_at: string;
}

export interface ChannelListResponse {
  channels: Channel[];
  total: number;
}

export interface ChannelCreate {
  platform: ChannelPlatform;
  credentials: Record<string, string>;
  bot_name: string;
  agent_id: string;
  skill_id?: string;
  workflow_id?: string;
  workflow_mappings?: Record<string, string>;
  daily_credit_limit?: number;
  low_balance_threshold?: number;
  pause_on_limit?: boolean;
  privacy_notice_url?: string;
}

export interface ChannelUpdate {
  bot_name?: string;
  agent_id?: string;
  skill_id?: string;
  daily_credit_limit?: number;
  low_balance_threshold?: number;
  pause_on_limit?: boolean;
  status?: "active" | "paused";
}

export interface ChannelAnalytics {
  channel_id: string;
  period_days: number;
  daily_messages: { date: string; count: number }[];
  daily_credits: { date: string; amount: number }[];
  top_users: { platform_user_id: string; message_count: number }[];
  cost_breakdown: {
    agent_processing: number;
    platform_surcharge: number;
    total: number;
    avg_per_message: number;
  };
}

export interface ChannelTestResult {
  success: boolean;
  message: string;
  latency_ms?: number;
}

export interface ChannelContact {
  platform_user_id_hash: string;
  message_count: number;
  last_seen: string;
  first_seen: string;
  is_blocked: boolean;
}

export interface ChannelContactList {
  contacts: ChannelContact[];
  total: number;
}

export interface ChannelMessage {
  id: string;
  direction: "inbound" | "outbound" | "system";
  platform_user_id_hash: string;
  message_text: string | null;
  credits_charged: number;
  response_time_ms: number | null;
  created_at: string;
}

export interface ChannelMessageList {
  messages: ChannelMessage[];
  cursor: string | null;
  has_more: boolean;
}

export interface AdminChannel extends Channel {
  owner_email: string;
  owner_name: string;
  owner_credit_balance: number;
  owner_account_tier: string;
}
