// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  GitBranch,
  Languages,
  Search,
  Code2,
  FileText,
  ArrowLeft,
  Workflow,
  Sparkles,
  Loader2,
} from "lucide-react";
import { useCreateWorkflow } from "@/lib/hooks/use-workflows";
import { useSupervisorPlan } from "@/lib/hooks/use-supervisor";
import { ROUTES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { WorkflowCreate, SupervisorPlan } from "@/types/workflow";
import { SupervisorPlanView } from "./supervisor-plan";

const TEMPLATES = [
  {
    id: "blank",
    icon: <FileText className="h-5 w-5" />,
    name: "Blank Workflow",
    description: "Start from scratch",
    steps: [] as WorkflowCreate["steps"],
  },
  {
    id: "translate-summarize",
    icon: <Languages className="h-5 w-5" />,
    name: "Translate & Summarize",
    description: "Translate text then summarize it",
    steps: [],
  },
  {
    id: "research-review",
    icon: <Search className="h-5 w-5" />,
    name: "Research & Review",
    description: "Research a topic then review the findings",
    steps: [],
  },
  {
    id: "code-qa",
    icon: <Code2 className="h-5 w-5" />,
    name: "Code & QA",
    description: "Generate code, then review and QA in parallel",
    steps: [],
  },
];

const PATTERNS = [
  {
    key: "manual" as const,
    icon: GitBranch,
    title: "Manual Pipeline",
    desc: "You pick agents & order. Sequential and parallel chains.",
    best: "Simple multi-step tasks",
  },
  {
    key: "hierarchical" as const,
    icon: Workflow,
    title: "Hierarchical Pipeline",
    desc: "Nested sub-workflows. Reusable pipeline building blocks.",
    best: "Complex multi-stage processes",
    badge: "Coming Soon",
  },
  {
    key: "supervisor" as const,
    icon: Sparkles,
    title: "Supervisor (AI-Planned)",
    desc: "Describe your goal. AI selects agents & builds the plan.",
    best: "\"I know what, not who\"",
  },
];

type PatternType = "manual" | "hierarchical" | "supervisor";

function NewWorkflowContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const createWorkflow = useCreateWorkflow();
  const planMutation = useSupervisorPlan();

  const [selectedPattern, setSelectedPattern] = useState<PatternType | null>(
    (searchParams.get("pattern") as PatternType) || null
  );
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [supervisorGoal, setSupervisorGoal] = useState("");
  const [currentPlan, setCurrentPlan] = useState<SupervisorPlan | null>(null);

  async function handleCreate() {
    if (!name.trim()) return;

    const data: WorkflowCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      pattern_type: selectedPattern || "manual",
      steps: [],
    };

    const wf = await createWorkflow.mutateAsync(data);
    window.location.href = ROUTES.workflowDetail(wf.id);
  }

  return (
    <div>
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold">New Workflow</h1>
          <p className="mt-1 text-muted-foreground">
            Create a multi-step agent pipeline
          </p>
        </div>
      </div>

      {/* Pattern selection */}
      {!selectedPattern && (
        <div className="mt-6">
          <Label className="text-sm font-medium">Choose a pattern</Label>
          <div className="mt-2 grid gap-4 sm:grid-cols-3">
            {PATTERNS.map((p) => (
              <Card
                key={p.key}
                className={cn(
                  "cursor-pointer transition-all hover:border-primary/50",
                  selectedPattern === p.key && "border-primary"
                )}
                onClick={() => setSelectedPattern(p.key)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <p.icon className="h-5 w-5 text-primary" />
                    <CardTitle className="text-base">{p.title}</CardTitle>
                  </div>
                  {p.badge && (
                    <Badge variant="secondary" className="w-fit text-xs">
                      {p.badge}
                    </Badge>
                  )}
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">{p.desc}</p>
                  <p className="mt-2 text-xs font-medium text-primary/70">
                    Best for: {p.best}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Manual / Hierarchical: template picker + name/description form */}
      {selectedPattern && selectedPattern !== "supervisor" && (
        <>
          <div className="mt-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setSelectedPattern(null)}
            >
              <ArrowLeft className="mr-1 h-3 w-3" />
              Back to patterns
            </Button>
          </div>

          {/* Template selection */}
          <div className="mt-4">
            <Label className="text-sm font-medium">
              Start from a template (optional)
            </Label>
            <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => {
                    setSelectedTemplate(t.id);
                    if (!name)
                      setName(t.name === "Blank Workflow" ? "" : t.name);
                  }}
                  className={`rounded-xl border p-4 text-left transition-all hover:border-primary/50 ${
                    selectedTemplate === t.id
                      ? "border-primary bg-primary/5"
                      : "bg-card"
                  }`}
                >
                  <div className="flex items-center gap-2 text-sm font-medium">
                    {t.icon}
                    {t.name}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {t.description}
                  </p>
                </button>
              ))}
            </div>
          </div>

          {/* Workflow details */}
          <div className="mt-6 max-w-lg space-y-4">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="My Pipeline"
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="What does this workflow do?"
                className="mt-1"
                rows={3}
              />
            </div>
            <Button
              onClick={handleCreate}
              disabled={!name.trim() || createWorkflow.isPending}
            >
              <GitBranch className="mr-2 h-4 w-4" />
              {createWorkflow.isPending ? "Creating..." : "Create Workflow"}
            </Button>
          </div>
        </>
      )}

      {/* Supervisor: goal textarea + generate plan */}
      {selectedPattern === "supervisor" && (
        <>
          <div className="mt-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSelectedPattern(null);
                setCurrentPlan(null);
              }}
            >
              <ArrowLeft className="mr-1 h-3 w-3" />
              Back to patterns
            </Button>
          </div>

          {!currentPlan && (
            <div className="mt-4 max-w-lg space-y-4">
              <div>
                <Label htmlFor="goal">Describe your goal</Label>
                <Textarea
                  id="goal"
                  value={supervisorGoal}
                  onChange={(e) => setSupervisorGoal(e.target.value)}
                  placeholder="Describe your goal... (e.g., Research competitor pricing and write a Spanish executive summary)"
                  className="mt-1"
                  rows={4}
                />
              </div>
              <Button
                onClick={async () => {
                  const plan = await planMutation.mutateAsync({
                    goal: supervisorGoal,
                  });
                  setCurrentPlan(plan);
                }}
                disabled={
                  supervisorGoal.length < 10 || planMutation.isPending
                }
              >
                {planMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Sparkles className="mr-2 h-4 w-4" />
                )}
                Generate Plan
              </Button>
              {planMutation.error && (
                <p className="text-sm text-destructive">
                  {planMutation.error.message || "Failed to generate plan"}
                </p>
              )}
            </div>
          )}

          {currentPlan && (
            <div className="mt-4 max-w-2xl">
              <SupervisorPlanView
                plan={currentPlan}
                goal={supervisorGoal}
                onEdit={(id) =>
                  (window.location.href = `/dashboard/workflows/${id}/`)
                }
                onReplan={(newPlan) => setCurrentPlan(newPlan)}
                onSaved={(id) =>
                  (window.location.href = `/dashboard/workflows/${id}/`)
                }
              />
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function NewWorkflowPage() {
  return (
    <Suspense fallback={<div className="p-8">Loading...</div>}>
      <NewWorkflowContent />
    </Suspense>
  );
}
