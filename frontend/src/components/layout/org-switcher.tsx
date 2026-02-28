"use client";

import { useState } from "react";
import { Building2, Check, ChevronsUpDown, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { useOrganizations, useCreateOrganization } from "@/lib/hooks/use-organizations";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface OrgSwitcherProps {
  selectedOrgId: string | null;
  onSelect: (orgId: string | null) => void;
}

export function OrgSwitcher({ selectedOrgId, onSelect }: OrgSwitcherProps) {
  const [open, setOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newSlug, setNewSlug] = useState("");

  const { data } = useOrganizations();
  const createOrg = useCreateOrganization();

  const selectedOrg = data?.organizations.find((o) => o.id === selectedOrgId);

  const handleCreate = async () => {
    if (!newName || !newSlug) return;
    const org = await createOrg.mutateAsync({ name: newName, slug: newSlug });
    onSelect(org.id);
    setDialogOpen(false);
    setNewName("");
    setNewSlug("");
  };

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between text-sm"
          >
            <div className="flex items-center gap-2 truncate">
              <Building2 className="h-4 w-4 shrink-0" />
              <span className="truncate">
                {selectedOrg?.name ?? "Personal"}
              </span>
            </div>
            <ChevronsUpDown className="ml-2 h-3 w-3 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-56 p-1" align="start">
          <button
            onClick={() => {
              onSelect(null);
              setOpen(false);
            }}
            className={cn(
              "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent",
              !selectedOrgId && "bg-accent"
            )}
          >
            {!selectedOrgId && <Check className="h-3 w-3" />}
            <span className={cn(!selectedOrgId ? "ml-0" : "ml-5")}>
              Personal
            </span>
          </button>

          {data?.organizations.map((org) => (
            <button
              key={org.id}
              onClick={() => {
                onSelect(org.id);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent",
                selectedOrgId === org.id && "bg-accent"
              )}
            >
              {selectedOrgId === org.id && <Check className="h-3 w-3" />}
              <span
                className={cn(selectedOrgId === org.id ? "ml-0" : "ml-5")}
              >
                {org.name}
              </span>
            </button>
          ))}

          <div className="border-t my-1" />
          <button
            onClick={() => {
              setOpen(false);
              setDialogOpen(true);
            }}
            className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <Plus className="h-3 w-3" />
            <span className="ml-2">Create Organization</span>
          </button>
        </PopoverContent>
      </Popover>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Organization</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label htmlFor="org-name">Name</Label>
              <Input
                id="org-name"
                value={newName}
                onChange={(e) => {
                  setNewName(e.target.value);
                  setNewSlug(
                    e.target.value
                      .toLowerCase()
                      .replace(/[^a-z0-9]+/g, "-")
                      .replace(/^-|-$/g, "")
                  );
                }}
                placeholder="My Organization"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="org-slug">Slug</Label>
              <Input
                id="org-slug"
                value={newSlug}
                onChange={(e) => setNewSlug(e.target.value)}
                placeholder="my-organization"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={handleCreate}
              disabled={!newName || !newSlug || createOrg.isPending}
            >
              {createOrg.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
