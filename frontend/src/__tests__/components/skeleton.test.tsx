import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import { Skeleton, SkeletonRow, SkeletonCard } from "@/app/components/ui/Skeleton";

describe("Skeleton", () => {
  it("renders a pulse placeholder", () => {
    const { container } = render(<Skeleton className="h-4 w-16" />);
    const el = container.querySelector("div.animate-pulse");
    expect(el).not.toBeNull();
    expect(el!.className).toContain("h-4");
  });

  it("SkeletonRow renders the row skeleton layout", () => {
    const { container } = render(<SkeletonRow />);
    expect(container.querySelectorAll("div.animate-pulse").length).toBeGreaterThan(0);
  });

  it("SkeletonCard renders the card skeleton layout", () => {
    const { container } = render(<SkeletonCard />);
    expect(container.querySelectorAll("div.animate-pulse").length).toBeGreaterThan(0);
  });
});
