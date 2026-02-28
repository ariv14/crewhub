export interface Organization {
  id: string;
  name: string;
  slug: string;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface OrganizationCreate {
  name: string;
  slug: string;
  avatar_url?: string | null;
}

export interface OrganizationUpdate {
  name?: string;
  slug?: string;
  avatar_url?: string | null;
}

export interface Team {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  created_at: string;
}

export interface TeamCreate {
  name: string;
  description?: string | null;
}

export interface Membership {
  id: string;
  user_id: string;
  organization_id: string;
  team_id: string | null;
  role: "viewer" | "member" | "admin" | "owner";
  created_at: string;
  user_email?: string | null;
  user_name?: string | null;
}

export interface MembershipCreate {
  user_email: string;
  role?: "viewer" | "member" | "admin" | "owner";
  team_id?: string | null;
}

export interface OrganizationListResponse {
  organizations: Organization[];
  total: number;
}

export interface TeamListResponse {
  teams: Team[];
  total: number;
}

export interface MembershipListResponse {
  members: Membership[];
  total: number;
}
