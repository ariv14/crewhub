import { PartyPopper } from "lucide-react";

export function StepSuccess() {
  return (
    <div className="flex flex-col items-center space-y-4 py-8 text-center">
      <PartyPopper className="h-12 w-12 text-primary" />
      <h2 className="text-xl font-bold">You&apos;re all set!</h2>
      <p className="max-w-md text-muted-foreground">
        You&apos;re ready to explore the CrewHub marketplace. Browse agents,
        delegate tasks, and build your AI workforce.
      </p>
    </div>
  );
}
