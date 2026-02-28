import { api } from "../api-client";
import type {
  Organization,
  OrganizationCreate,
  OrganizationUpdate,
  OrganizationListResponse,
  Team,
  TeamCreate,
  TeamListResponse,
  Membership,
  MembershipCreate,
  MembershipListResponse,
} from "@/types/organization";

// ── Organizations ────────────────────────────────────────────

export async function listOrganizations(): Promise<OrganizationListResponse> {
  return api.get<OrganizationListResponse>("/organizations");
}

export async function getOrganization(id: string): Promise<Organization> {
  return api.get<Organization>(`/organizations/${id}`);
}

export async function createOrganization(
  data: OrganizationCreate
): Promise<Organization> {
  return api.post<Organization>("/organizations", data);
}

export async function updateOrganization(
  id: string,
  data: OrganizationUpdate
): Promise<Organization> {
  return api.patch<Organization>(`/organizations/${id}`, data);
}

export async function deleteOrganization(id: string): Promise<void> {
  return api.delete(`/organizations/${id}`);
}

// ── Teams ────────────────────────────────────────────────────

export async function listTeams(orgId: string): Promise<TeamListResponse> {
  return api.get<TeamListResponse>(`/organizations/${orgId}/teams`);
}

export async function createTeam(
  orgId: string,
  data: TeamCreate
): Promise<Team> {
  return api.post<Team>(`/organizations/${orgId}/teams`, data);
}

export async function deleteTeam(
  orgId: string,
  teamId: string
): Promise<void> {
  return api.delete(`/organizations/${orgId}/teams/${teamId}`);
}

// ── Members ──────────────────────────────────────────────────

export async function listMembers(
  orgId: string
): Promise<MembershipListResponse> {
  return api.get<MembershipListResponse>(`/organizations/${orgId}/members`);
}

export async function inviteMember(
  orgId: string,
  data: MembershipCreate
): Promise<Membership> {
  return api.post<Membership>(`/organizations/${orgId}/members`, data);
}

export async function updateMemberRole(
  orgId: string,
  membershipId: string,
  role: string
): Promise<Membership> {
  return api.patch<Membership>(
    `/organizations/${orgId}/members/${membershipId}`,
    { role }
  );
}

export async function removeMember(
  orgId: string,
  membershipId: string
): Promise<void> {
  return api.delete(`/organizations/${orgId}/members/${membershipId}`);
}
