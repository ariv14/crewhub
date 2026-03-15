// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import type { Agent, Skill } from "./agent";

export interface CrewMember {
  id: string;
  agent_id: string;
  skill_id: string;
  position: number;
  agent: Agent;
  skill: Skill;
}

export interface Crew {
  id: string;
  owner_id: string;
  name: string;
  description: string | null;
  icon: string;
  is_public: boolean;
  members: CrewMember[];
  created_at: string;
  updated_at: string;
}

export interface CrewCreate {
  name: string;
  description?: string;
  icon?: string;
  is_public?: boolean;
  members: { agent_id: string; skill_id: string; position: number }[];
}

export interface CrewUpdate {
  name?: string;
  description?: string;
  icon?: string;
  is_public?: boolean;
  members?: { agent_id: string; skill_id: string; position: number }[];
}

export interface CrewListResponse {
  crews: Crew[];
  total: number;
}

export interface CrewRunRequest {
  message: string;
}

export interface CrewRunResponse {
  crew_id: string;
  task_ids: string[];
  member_task_map: Record<string, string>;
}
