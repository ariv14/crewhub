import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface StepWelcomeProps {
  name: string;
  setName: (name: string) => void;
}

export function StepWelcome({ name, setName }: StepWelcomeProps) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">Welcome to CrewHub</h2>
        <p className="mt-1 text-muted-foreground">
          Let&apos;s get you set up. First, tell us your name.
        </p>
      </div>
      <div className="space-y-2">
        <Label>Your Name</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="What should we call you?"
        />
      </div>
    </div>
  );
}
