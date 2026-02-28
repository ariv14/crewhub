import { CATEGORIES } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface StepInterestsProps {
  interests: string[];
  setInterests: (interests: string[]) => void;
}

export function StepInterests({ interests, setInterests }: StepInterestsProps) {
  function toggle(slug: string) {
    setInterests(
      interests.includes(slug)
        ? interests.filter((i) => i !== slug)
        : [...interests, slug]
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-bold">What are you interested in?</h2>
        <p className="mt-1 text-muted-foreground">
          Select categories to get personalized agent recommendations.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.slug}
            onClick={() => toggle(cat.slug)}
            className={cn(
              "rounded-lg border p-3 text-left text-sm font-medium transition-colors",
              interests.includes(cat.slug)
                ? "border-primary bg-primary/10 text-primary"
                : "hover:bg-muted"
            )}
          >
            {cat.label}
          </button>
        ))}
      </div>
    </div>
  );
}
