import type { NegotiationResult } from "../../types/inspection";

interface LiveNegotiationPanelProps {
  totalRepairCost: number;
  negotiation: NegotiationResult;
}

const RECOMMENDATION_LABEL: Record<NegotiationResult["recommendation"], string> = {
  BUY: "Comprar",
  NEGOTIATE: "Negociar",
  WALK_AWAY: "No comprar",
};

const RECOMMENDATION_STYLE: Record<NegotiationResult["recommendation"], string> = {
  BUY: "bg-green-100 text-green-800",
  NEGOTIATE: "bg-yellow-100 text-yellow-800",
  WALK_AWAY: "bg-red-100 text-red-800",
};

function formatEur(value: number): string {
  return new Intl.NumberFormat("es-ES", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(Math.round(value || 0));
}

export function LiveNegotiationPanel({
  totalRepairCost,
  negotiation,
}: LiveNegotiationPanelProps) {
  const recommendation = negotiation.recommendation;
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-amber-900">
          Negociación en vivo
        </h2>
        <span className="rounded-full bg-amber-200 px-2 py-0.5 text-xs font-medium text-amber-900">
          actualizado al instante
        </span>
      </div>
      <p className="mt-1 text-xs text-amber-800">
        Coste total de reparación: {formatEur(totalRepairCost)} €
      </p>
      <dl className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <dt className="text-xs text-amber-700">Oferta recomendada</dt>
          <dd className="text-lg font-bold text-amber-900">
            {formatEur(negotiation.recommended_initial_offer)} €
          </dd>
        </div>
        <div>
          <dt className="text-xs text-amber-700">Precio máx. compra</dt>
          <dd className="text-lg font-bold text-amber-900">
            {formatEur(negotiation.maximum_purchase_price)} €
          </dd>
        </div>
        <div>
          <dt className="text-xs text-amber-700">Beneficio esperado</dt>
          <dd className="text-lg font-bold text-amber-900">
            {formatEur(negotiation.expected_profit)} €
          </dd>
        </div>
        <div>
          <dt className="text-xs text-amber-700">Recomendación</dt>
          <dd
            className={`mt-1 inline-block rounded-full px-2 py-0.5 text-sm font-semibold ${RECOMMENDATION_STYLE[recommendation]}`}
          >
            {RECOMMENDATION_LABEL[recommendation]}
          </dd>
        </div>
      </dl>
    </div>
  );
}
