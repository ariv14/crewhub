// Copyright (c) 2026 CrewHub. All rights reserved.
// Proprietary and confidential. See LICENSE for details.
import Image from "next/image";
import { cn } from "@/lib/utils";

const sizes = {
  sm: 20,
  md: 28,
  lg: 40,
  hero: 72,
} as const;

// Orbit radius and particle size scale with logo size
const orbitConfig: Record<keyof typeof sizes, { radius: number; dot: number }> = {
  sm: { radius: 14, dot: 2 },
  md: { radius: 18, dot: 2.5 },
  lg: { radius: 26, dot: 3 },
  hero: { radius: 44, dot: 4 },
};

interface SpinningLogoProps {
  spinning?: boolean;
  size?: keyof typeof sizes;
  className?: string;
  orbits?: boolean;
}

export function SpinningLogo({
  spinning = false,
  size = "md",
  className,
  orbits = true,
}: SpinningLogoProps) {
  const px = sizes[size];
  const { radius, dot } = orbitConfig[size];

  return (
    <span
      className="logo-orbit-container"
      style={{
        position: "relative",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: px + radius * 2,
        height: px + radius * 2,
      }}
    >
      <Image
        src="/logo.svg"
        alt="CrewHub"
        width={px}
        height={px}
        className={cn(
          spinning && "logo-spinning logo-glow",
          className,
        )}
        priority={size === "lg" || size === "hero"}
      />
      {orbits && (
        <>
          <span
            className="logo-orbit-dot logo-orbit-1"
            style={{
              "--orbit-radius": `${radius}px`,
              "--dot-size": `${dot}px`,
              "--dot-color": "#6366f1",
            } as React.CSSProperties}
          />
          <span
            className="logo-orbit-dot logo-orbit-2"
            style={{
              "--orbit-radius": `${radius}px`,
              "--dot-size": `${dot}px`,
              "--dot-color": "#06b6d4",
            } as React.CSSProperties}
          />
          <span
            className="logo-orbit-dot logo-orbit-3"
            style={{
              "--orbit-radius": `${radius}px`,
              "--dot-size": `${dot}px`,
              "--dot-color": "#a78bfa",
            } as React.CSSProperties}
          />
        </>
      )}
    </span>
  );
}
