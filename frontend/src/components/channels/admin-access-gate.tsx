// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Label } from "@/components/ui/label";

const JUSTIFICATION_OPTIONS = [
  "Abuse report investigation",
  "Developer-requested support",
  "Legal/regulatory request",
  "Platform compliance check",
] as const;

type Justification = (typeof JUSTIFICATION_OPTIONS)[number];

interface AdminAccessGateProps {
  onConfirm: (justification: string) => void;
  onCancel: () => void;
}

export function AdminAccessGate({ onConfirm, onCancel }: AdminAccessGateProps) {
  const [selected, setSelected] = useState<Justification | null>(null);

  return (
    <AlertDialog open onOpenChange={(open) => !open && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Access Justification Required</AlertDialogTitle>
          <AlertDialogDescription>
            Admin access to channel messages is audit-logged per SOC 2 CC7.2. Select a reason.
          </AlertDialogDescription>
        </AlertDialogHeader>

        <fieldset className="space-y-2 py-1">
          <legend className="sr-only">Select justification</legend>
          {JUSTIFICATION_OPTIONS.map((option) => (
            <div key={option} className="flex items-center gap-3">
              <input
                type="radio"
                id={option}
                name="justification"
                value={option}
                checked={selected === option}
                onChange={() => setSelected(option)}
                className="h-4 w-4 accent-primary"
              />
              <Label htmlFor={option} className="cursor-pointer font-normal">
                {option}
              </Label>
            </div>
          ))}
        </fieldset>

        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            disabled={!selected}
            onClick={() => selected && onConfirm(selected)}
          >
            Access Messages
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
