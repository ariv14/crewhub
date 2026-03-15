// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { Building2, Plus, Trash2, Users } from "lucide-react";
import { OrgSwitcher } from "@/components/layout/org-switcher";
import {
  useMembers,
  useTeams,
  useInviteMember,
  useCreateTeam,
  useRemoveMember,
  useDeleteTeam,
} from "@/lib/hooks/use-organizations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  admin: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  member: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  viewer: "bg-zinc-500/15 text-zinc-400 border-zinc-500/30",
};

export default function TeamPage() {
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [newTeamName, setNewTeamName] = useState("");

  const orgId = selectedOrgId ?? "";
  const { data: members } = useMembers(orgId);
  const { data: teams } = useTeams(orgId);
  const inviteMember = useInviteMember(orgId);
  const createTeam = useCreateTeam(orgId);
  const removeMember = useRemoveMember(orgId);
  const deleteTeam = useDeleteTeam(orgId);

  const handleInvite = async () => {
    if (!inviteEmail || !selectedOrgId) return;
    await inviteMember.mutateAsync({
      user_email: inviteEmail,
      role: inviteRole as "viewer" | "member" | "admin" | "owner",
    });
    setInviteEmail("");
  };

  const handleCreateTeam = async () => {
    if (!newTeamName || !selectedOrgId) return;
    await createTeam.mutateAsync({ name: newTeamName });
    setNewTeamName("");
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Team Management</h1>
        <p className="mt-1 text-muted-foreground">
          Manage your organization, teams, and members
        </p>
      </div>

      <div className="max-w-xs">
        <OrgSwitcher
          selectedOrgId={selectedOrgId}
          onSelect={setSelectedOrgId}
        />
      </div>

      {!selectedOrgId ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12">
            <Building2 className="h-10 w-10 text-muted-foreground" />
            <p className="text-muted-foreground">
              Select or create an organization to manage teams and members
            </p>
          </CardContent>
        </Card>
      ) : (
        <Tabs defaultValue="members">
          <TabsList>
            <TabsTrigger value="members">
              <Users className="mr-1.5 h-4 w-4" />
              Members
            </TabsTrigger>
            <TabsTrigger value="teams">
              <Building2 className="mr-1.5 h-4 w-4" />
              Teams
            </TabsTrigger>
          </TabsList>

          <TabsContent value="members" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Invite Member</CardTitle>
                <CardDescription>
                  Add a team member by their email address
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Input
                    placeholder="user@example.com"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    className="max-w-sm"
                  />
                  <Select value={inviteRole} onValueChange={setInviteRole}>
                    <SelectTrigger className="w-32">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="viewer">Viewer</SelectItem>
                      <SelectItem value="member">Member</SelectItem>
                      <SelectItem value="admin">Admin</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    onClick={handleInvite}
                    disabled={!inviteEmail || inviteMember.isPending}
                  >
                    <Plus className="mr-1.5 h-4 w-4" />
                    Invite
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Email</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Joined</TableHead>
                      <TableHead className="w-12" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {members?.members.map((m) => (
                      <TableRow key={m.id}>
                        <TableCell className="font-medium">
                          {m.user_email ?? m.user_id.slice(0, 8)}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className={ROLE_COLORS[m.role] ?? ""}
                          >
                            {m.role}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {new Date(m.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell>
                          {m.role !== "owner" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => removeMember.mutate(m.id)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                    {(!members || members.members.length === 0) && (
                      <TableRow>
                        <TableCell
                          colSpan={4}
                          className="text-center text-muted-foreground py-8"
                        >
                          No members yet
                        </TableCell>
                      </TableRow>
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="teams" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Create Team</CardTitle>
                <CardDescription>
                  Organize members into teams within this organization
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Input
                    placeholder="Team name"
                    value={newTeamName}
                    onChange={(e) => setNewTeamName(e.target.value)}
                    className="max-w-sm"
                  />
                  <Button
                    onClick={handleCreateTeam}
                    disabled={!newTeamName || createTeam.isPending}
                  >
                    <Plus className="mr-1.5 h-4 w-4" />
                    Create
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {teams?.teams.map((team) => (
                <Card key={team.id}>
                  <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-base">{team.name}</CardTitle>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => deleteTeam.mutate(team.id)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </CardHeader>
                  {team.description && (
                    <CardContent>
                      <p className="text-sm text-muted-foreground">
                        {team.description}
                      </p>
                    </CardContent>
                  )}
                </Card>
              ))}
              {(!teams || teams.teams.length === 0) && (
                <Card className="col-span-full">
                  <CardContent className="flex items-center justify-center py-8 text-muted-foreground">
                    No teams yet
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
