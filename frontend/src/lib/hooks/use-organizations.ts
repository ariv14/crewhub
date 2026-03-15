// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as orgsApi from "../api/organizations";
import type {
  OrganizationCreate,
  OrganizationUpdate,
  MembershipCreate,
  TeamCreate,
} from "@/types/organization";

// ── Organizations ────────────────────────────────────────────

export function useOrganizations() {
  return useQuery({
    queryKey: ["organizations"],
    queryFn: orgsApi.listOrganizations,
  });
}

export function useOrganization(id: string) {
  return useQuery({
    queryKey: ["organizations", id],
    queryFn: () => orgsApi.getOrganization(id),
    enabled: !!id,
  });
}

export function useCreateOrganization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: OrganizationCreate) => orgsApi.createOrganization(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["organizations"] }),
  });
}

export function useUpdateOrganization(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: OrganizationUpdate) =>
      orgsApi.updateOrganization(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["organizations", id] });
      qc.invalidateQueries({ queryKey: ["organizations"] });
    },
  });
}

export function useDeleteOrganization() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => orgsApi.deleteOrganization(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["organizations"] }),
  });
}

// ── Teams ────────────────────────────────────────────────────

export function useTeams(orgId: string) {
  return useQuery({
    queryKey: ["organizations", orgId, "teams"],
    queryFn: () => orgsApi.listTeams(orgId),
    enabled: !!orgId,
  });
}

export function useCreateTeam(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: TeamCreate) => orgsApi.createTeam(orgId, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "teams"] }),
  });
}

export function useDeleteTeam(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (teamId: string) => orgsApi.deleteTeam(orgId, teamId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "teams"] }),
  });
}

// ── Members ──────────────────────────────────────────────────

export function useMembers(orgId: string) {
  return useQuery({
    queryKey: ["organizations", orgId, "members"],
    queryFn: () => orgsApi.listMembers(orgId),
    enabled: !!orgId,
  });
}

export function useInviteMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: MembershipCreate) => orgsApi.inviteMember(orgId, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "members"] }),
  });
}

export function useUpdateMemberRole(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ membershipId, role }: { membershipId: string; role: string }) =>
      orgsApi.updateMemberRole(orgId, membershipId, role),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "members"] }),
  });
}

export function useRemoveMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (membershipId: string) =>
      orgsApi.removeMember(orgId, membershipId),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["organizations", orgId, "members"] }),
  });
}
