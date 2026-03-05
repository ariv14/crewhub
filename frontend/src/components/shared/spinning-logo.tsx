import Image from "next/image";
import { cn } from "@/lib/utils";

const sizes = {
  sm: 20,
  md: 28,
  lg: 40,
} as const;

interface SpinningLogoProps {
  spinning?: boolean;
  size?: keyof typeof sizes;
  className?: string;
}

export function SpinningLogo({
  spinning = false,
  size = "md",
  className,
}: SpinningLogoProps) {
  const px = sizes[size];

  return (
    <Image
      src="/logo.svg"
      alt="CrewHub"
      width={px}
      height={px}
      className={cn(
        spinning && "logo-spinning logo-glow",
        className,
      )}
      priority={size === "lg"}
    />
  );
}
