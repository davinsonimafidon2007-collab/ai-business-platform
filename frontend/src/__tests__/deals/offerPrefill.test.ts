import { describe, it, expect } from "vitest";
import { offerPricePrefill } from "@/app/(app)/deals/offerPrefill";

describe("offerPricePrefill", () => {
  it("devuelve string del last_sim_purchase_price", () => {
    expect(offerPricePrefill({ last_sim_purchase_price: 12500.5 })).toBe(
      "12500.5"
    );
  });

  it("devuelve vacío si no hay simulación", () => {
    expect(offerPricePrefill({ last_sim_purchase_price: null })).toBe("");
    expect(offerPricePrefill({ last_sim_purchase_price: undefined })).toBe("");
  });

  it("acepta 0 como valor válido", () => {
    expect(offerPricePrefill({ last_sim_purchase_price: 0 })).toBe("0");
  });
});
