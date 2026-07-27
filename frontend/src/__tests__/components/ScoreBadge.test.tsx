import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScoreBadge, ProfitBadge, OpportunityBadge, RecommendationBadge } from "@/app/components/ui/ScoreBadge";

describe("ScoreBadge", () => {
  it("renders score value", () => {
    render(<ScoreBadge score={85} />);
    expect(screen.getByText("85")).toBeDefined();
  });

  it("applies green color for high scores", () => {
    render(<ScoreBadge score={90} />);
    const badge = screen.getByText("90");
    expect(badge.className).toContain("bg-green-100");
  });

  it("applies red color for low scores", () => {
    render(<ScoreBadge score={20} />);
    const badge = screen.getByText("20");
    expect(badge.className).toContain("bg-red-100");
  });
});

describe("ProfitBadge", () => {
  it("shows positive profit with + sign", () => {
    render(<ProfitBadge value={1500} />);
    expect(screen.getByText("+€1.500")).toBeDefined();
  });

  it("shows negative profit without + sign", () => {
    render(<ProfitBadge value={-500} />);
    expect(screen.getByText("-€500")).toBeDefined();
  });
});

describe("OpportunityBadge", () => {
  it("renders EXCELLENT as Excelente", () => {
    render(<OpportunityBadge level="EXCELLENT" />);
    expect(screen.getByText("Excelente")).toBeDefined();
  });

  it("renders REJECT as Rechazado", () => {
    render(<OpportunityBadge level="REJECT" />);
    expect(screen.getByText("Rechazado")).toBeDefined();
  });
});

describe("RecommendationBadge", () => {
  it("renders BUY_NOW as Comprar ahora", () => {
    render(<RecommendationBadge recommendation="BUY_NOW" />);
    expect(screen.getByText("Comprar ahora")).toBeDefined();
  });

  it("renders REJECT as Rechazar", () => {
    render(<RecommendationBadge recommendation="REJECT" />);
    expect(screen.getByText("Rechazar")).toBeDefined();
  });
});