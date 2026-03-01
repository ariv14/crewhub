"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { StepWelcome } from "./step-welcome";
import { StepApiKeys } from "./step-api-keys";
import { StepInterests } from "./step-interests";
import { StepRecommended } from "./step-recommended";
import { StepTryAgent } from "./step-try-agent";
import { StepSuccess } from "./step-success";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { ROUTES } from "@/lib/constants";

const STEPS = ["Welcome", "API Keys", "Interests", "Recommended", "Try It", "Done"];

export function OnboardingWizard() {
  const router = useRouter();
  const { refreshUser } = useAuth();
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [interests, setInterests] = useState<string[]>([]);

  async function handleComplete() {
    try {
      await api.post("/auth/onboarding", { name: name || undefined, interests });
      await refreshUser?.();
      toast.success("Onboarding complete!");
      router.push(ROUTES.dashboard);
    } catch {
      toast.error("Failed to save onboarding");
    }
  }

  const progress = ((step + 1) / STEPS.length) * 100;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Progress value={progress} className="h-2" />

      <div className="flex gap-2">
        {STEPS.map((s, i) => (
          <span
            key={s}
            className={`rounded-full px-3 py-1 text-xs font-medium ${
              i === step
                ? "bg-primary text-primary-foreground"
                : i < step
                  ? "bg-primary/20 text-primary"
                  : "bg-muted text-muted-foreground"
            }`}
          >
            {i < step ? <Check className="inline h-3 w-3" /> : null} {s}
          </span>
        ))}
      </div>

      <Card>
        <CardContent className="p-6">
          {step === 0 && <StepWelcome name={name} setName={setName} />}
          {step === 1 && <StepApiKeys />}
          {step === 2 && (
            <StepInterests interests={interests} setInterests={setInterests} />
          )}
          {step === 3 && <StepRecommended interests={interests} />}
          {step === 4 && <StepTryAgent interests={interests} />}
          {step === 5 && <StepSuccess />}

          <div className="mt-6 flex justify-between">
            <Button
              variant="outline"
              onClick={() => setStep((s) => s - 1)}
              disabled={step === 0}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button onClick={() => setStep((s) => s + 1)}>
                Next
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Button onClick={handleComplete}>Go to Dashboard</Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
