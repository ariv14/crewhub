"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  GitBranch,
  Languages,
  Search,
  Code2,
  FileText,
  ArrowLeft,
} from "lucide-react";
import { useCreateWorkflow } from "@/lib/hooks/use-workflows";
import { ROUTES } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import type { WorkflowCreate } from "@/types/workflow";

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

export default function NewWorkflowPage() {
  const router = useRouter();
  const createWorkflow = useCreateWorkflow();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

  async function handleCreate() {
    if (!name.trim()) return;

    const data: WorkflowCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
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

      {/* Template selection */}
      <div className="mt-6">
        <Label className="text-sm font-medium">
          Start from a template (optional)
        </Label>
        <div className="mt-2 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {TEMPLATES.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                setSelectedTemplate(t.id);
                if (!name) setName(t.name === "Blank Workflow" ? "" : t.name);
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
    </div>
  );
}
