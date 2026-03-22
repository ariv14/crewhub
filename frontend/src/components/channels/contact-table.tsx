// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import { toast } from "sonner";
import { ShieldOff, ShieldCheck, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { formatRelativeTime } from "@/lib/utils";
import {
  useContacts,
  useBlockContact,
  useUnblockContact,
  useDeleteContactData,
} from "@/lib/hooks/use-channels";

interface ContactTableProps {
  channelId: string;
}

export function ContactTable({ channelId }: ContactTableProps) {
  const { data, isLoading } = useContacts(channelId);
  const blockContact = useBlockContact();
  const unblockContact = useUnblockContact();
  const deleteContactData = useDeleteContactData();
  const [pendingDelete, setPendingDelete] = useState<string | null>(null);

  if (isLoading) {
    return <p className="py-8 text-center text-sm text-muted-foreground">Loading contacts…</p>;
  }

  if (!data?.contacts.length) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No contacts yet — messages from your bot&apos;s users will appear here
      </p>
    );
  }

  function handleBlock(userHash: string) {
    blockContact.mutate(
      { channelId, userHash },
      {
        onSuccess: () => toast.success("Contact blocked"),
        onError: () => toast.error("Failed to block contact"),
      }
    );
  }

  function handleUnblock(userHash: string) {
    unblockContact.mutate(
      { channelId, userHash },
      {
        onSuccess: () => toast.success("Contact unblocked"),
        onError: () => toast.error("Failed to unblock contact"),
      }
    );
  }

  function handleDeleteData(userHash: string) {
    deleteContactData.mutate(
      { channelId, userHash },
      {
        onSuccess: () => {
          toast.success("Contact data deleted");
          setPendingDelete(null);
        },
        onError: () => {
          toast.error("Failed to delete contact data");
          setPendingDelete(null);
        },
      }
    );
  }

  return (
    <div className="rounded-md border">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/40">
            <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">User</th>
            <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Messages</th>
            <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Last Seen</th>
            <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Status</th>
            <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.contacts.map((contact) => {
            const shortHash = contact.platform_user_id_hash.slice(0, 8) + "...";
            return (
              <tr key={contact.platform_user_id_hash} className="border-b last:border-0 hover:bg-muted/20">
                <td className="px-4 py-3 font-mono text-xs">{shortHash}</td>
                <td className="px-4 py-3">{contact.message_count}</td>
                <td className="px-4 py-3 text-muted-foreground">
                  {formatRelativeTime(contact.last_seen)}
                </td>
                <td className="px-4 py-3">
                  {contact.is_blocked ? (
                    <Badge variant="outline" className="bg-red-500/10 text-red-400 border-red-500/30">
                      Blocked
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/30">
                      Active
                    </Badge>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-end gap-1">
                    {contact.is_blocked ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleUnblock(contact.platform_user_id_hash)}
                        disabled={unblockContact.isPending}
                      >
                        <ShieldCheck className="h-3.5 w-3.5 mr-1" />
                        Unblock
                      </Button>
                    ) : (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleBlock(contact.platform_user_id_hash)}
                        disabled={blockContact.isPending}
                      >
                        <ShieldOff className="h-3.5 w-3.5 mr-1" />
                        Block
                      </Button>
                    )}
                    <AlertDialog
                      open={pendingDelete === contact.platform_user_id_hash}
                      onOpenChange={(open) => !open && setPendingDelete(null)}
                    >
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive"
                          onClick={() => setPendingDelete(contact.platform_user_id_hash)}
                        >
                          <Trash2 className="h-3.5 w-3.5 mr-1" />
                          Delete Data
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete contact data?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will permanently delete all messages from this contact. This action
                            cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => handleDeleteData(contact.platform_user_id_hash)}
                            disabled={deleteContactData.isPending}
                          >
                            Delete permanently
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
