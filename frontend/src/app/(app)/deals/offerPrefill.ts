import type { Deal } from "@/app/services/deals";

/** Valor inicial del input de oferta al pasar a OFFER. */
export function offerPricePrefill(
  deal: Pick<Deal, "last_sim_purchase_price">
): string {
  if (deal.last_sim_purchase_price == null) return "";
  return String(deal.last_sim_purchase_price);
}
