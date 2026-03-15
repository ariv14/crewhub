// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
export type TransactionType =
  | "purchase"
  | "task_payment"
  | "refund"
  | "bonus"
  | "platform_fee";

export interface Balance {
  balance: number;
  reserved: number;
  available: number;
  currency: string;
}

export interface PurchaseRequest {
  amount: number;
}

export interface Transaction {
  id: string;
  from_account_id: string | null;
  to_account_id: string | null;
  amount: number;
  type: TransactionType;
  task_id: string | null;
  description: string;
  created_at: string;
}

export interface TransactionListResponse {
  transactions: Transaction[];
  total: number;
}

export interface UsageResponse {
  total_spent: number;
  total_earned: number;
  tasks_created: number;
  tasks_received: number;
  period: string;
}

export interface SpendByAgentItem {
  agent_id: string;
  agent_name: string;
  agent_category: string;
  tasks_count: number;
  total_spent: number;
  avg_cost: number;
}

export interface SpendByAgentResponse {
  breakdown: SpendByAgentItem[];
  period: string;
}
