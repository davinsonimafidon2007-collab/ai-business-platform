import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ScoreBadge, ProfitBadge, OpportunityBadge, RecommendationBadge, NegotiationBadge } from "@/app/components/ui/ScoreBadge";

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
    const { container } = render(<ProfitBadge value={1500} />);
    const badge = container.querySelector("span");
    expect(badge).toBeDefined();
    expect(badge?.textContent).toContain("+");
    expect(badge?.textContent).toContain("€");
    expect(badge?.textContent).toContain("1500");
  });

  it("shows negative profit without + sign", () => {
    const { container } = render(<ProfitBadge value={-500} />);
    const badge = container.querySelector("span");
    expect(badge).toBeDefined();
    expect(badge?.textContent).toContain("€");
    expect(badge?.textContent).toContain("-500");
    expect(badge?.textContent).not.toContain("+");
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

describe("ScoreBadge edge ranges", () => {
  it("renders an optional label", () => {
    render(<ScoreBadge score={70} label="Score" />);
    expect(screen.getByText("Score:")).toBeDefined();
  });

  it("applies blue color for 60-79", () => {
    render(<ScoreBadge score={70} />);
    expect(screen.getByText("70").className).toContain("bg-blue-100");
  });

  it("applies yellow color for 40-59", () => {
    render(<ScoreBadge score={50} />);
    expect(screen.getByText("50").className).toContain("bg-yellow-100");
  });

  it("applies the md size class", () => {
    render(<ScoreBadge score={85} size="md" />);
    expect(screen.getByText("85").className).toContain("px-2.5");
  });
});

describe("OpportunityBadge fallback", () => {
  it("falls back to POOR for unknown levels", () => {
    render(<OpportunityBadge level="UNKNOWN" />);
    expect(screen.getByText("Baja")).toBeDefined();
  });
});

describe("NegotiationBadge", () => {
  it("renders BUY as Comprar", () => {
    render(<NegotiationBadge recommendation="BUY" />);
    expect(screen.getByText("Comprar")).toBeDefined();
  });

  it("falls back to the raw recommendation when unknown", () => {
    render(<NegotiationBadge recommendation="CUSTOM" />);
    expect(screen.getByText("CUSTOM")).toBeDefined();
  });
});

describe("RecommendationBadge label + fallback", () => {
  it("uses the explicit label over the config mapping", () => {
    render(<RecommendationBadge recommendation="BUY_NOW" label="Comprar ya" />);
    expect(screen.getByText("Comprar ya")).toBeDefined();
  });

  it("falls back to the raw recommendation when not in config", () => {
    render(<RecommendationBadge recommendation="CUSTOM" />);
    expect(screen.getByText("CUSTOM")).toBeDefined();
  });
});