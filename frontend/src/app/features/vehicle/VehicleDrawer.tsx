"use client";

import { useEffect, useRef } from "react";
import { Button } from "@/app/components/ui/button";
import { ScoreBadge, OpportunityBadge, RecommendationBadge, NegotiationBadge } from "@/app/components/ui/ScoreBadge";
import type { SearchResultItem } from "@/app/types/vehicle";

interface VehicleDrawerProps {
  vehicle: SearchResultItem | null;
  onClose: () => void;
}

export function VehicleDrawer({ vehicle, onClose }: VehicleDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  if (!vehicle) return null;

  const vs = vehicle.vehicle_score;
  const me = vehicle.market_estimation;
  const pa = vehicle.profit_analysis;
  const opp = vehicle.opportunity;

  const formatEur = (val: number | null | undefined) =>
    val != null ? `€${val.toLocaleString("es-ES", { maximumFractionDigits: 2 })}` : "-";

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/50" onClick={onClose} />
      <div
        ref={drawerRef}
        className="fixed right-0 top-0 z-50 h-full w-full max-w-lg overflow-y-auto border-l border-secondary-200 bg-white shadow-xl dark:border-secondary-700 dark:bg-secondary-900"
      >
        <div className="sticky top-0 flex items-center justify-between border-b border-secondary-200 bg-white px-6 py-4 dark:border-secondary-700 dark:bg-secondary-900">
          <h2 className="text-lg font-bold text-secondary-900 dark:text-secondary-100">
            Detalle del vehículo
          </h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ✕
          </Button>
        </div>

        <div className="space-y-6 p-6">
          {/* Image */}
          {vehicle.images && vehicle.images[0] && (
            <img
              src={vehicle.images[0]}
              alt={`${vehicle.brand} ${vehicle.model}`}
              className="w-full rounded-lg object-cover"
              style={{ maxHeight: "240px" }}
            />
          )}

          {/* Basic Info */}
          <div className="grid grid-cols-2 gap-4">
            <InfoItem label="Marca" value={vehicle.brand} />
            <InfoItem label="Modelo" value={vehicle.model} />
            <InfoItem label="Año" value={vehicle.year?.toString()} />
            <InfoItem label="Kilómetros" value={vehicle.mileage ? `${(vehicle.mileage / 1000).toFixed(0)}k km` : "-"} />
            <InfoItem label="Precio" value={formatEur(vehicle.price)} />
            <InfoItem label="Ubicación" value={vehicle.location} />
            <InfoItem label="Proveedor" value={vehicle.source} />
            <InfoItem label="Combustible" value={vehicle.fuel_type} />
            <InfoItem label="Transmisión" value={vehicle.transmission} />
            <InfoItem label="Potencia" value={vehicle.power_hp ? `${vehicle.power_hp} HP` : "-"} />
          </div>

          {/* Vehicle Score */}
          {vs && (
            <Section title="Vehicle Score">
              <div className="flex items-center gap-3">
                <ScoreBadge score={vs.score} label="Score" size="md" />
                <span className="text-sm text-secondary-600 dark:text-secondary-400">{vs.category}</span>
              </div>
              {vs.strengths.length > 0 && (
                <div>
                  <p className="mb-1 text-sm font-medium text-green-600 dark:text-green-400">Fortalezas</p>
                  <ul className="list-inside list-disc text-sm text-secondary-600 dark:text-secondary-400">
                    {vs.strengths.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}
              {vs.weaknesses.length > 0 && (
                <div>
                  <p className="mb-1 text-sm font-medium text-red-600 dark:text-red-400">Debilidades</p>
                  <ul className="list-inside list-disc text-sm text-secondary-600 dark:text-secondary-400">
                    {vs.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}
            </Section>
          )}

          {/* Market Estimation */}
          {me && (
            <Section title="Market Estimation">
              <div className="grid grid-cols-2 gap-3">
                <InfoItem label="Precio de mercado" value={formatEur(me.market_price)} />
                <InfoItem label="Confianza" value={`${me.confidence.toFixed(1)}%`} />
                <InfoItem label="Oferta" value={`${me.supply_level.toFixed(0)}/100`} />
                <InfoItem label="Demanda" value={`${me.demand_level.toFixed(0)}/100`} />
                <InfoItem label="Tendencia" value={me.market_trend} />
                <InfoItem label="Comparables" value={me.comparable_count.toString()} />
              </div>
              {me.notes.length > 0 && (
                <div className="mt-2">
                  <p className="mb-1 text-sm font-medium text-secondary-700 dark:text-secondary-300">Notas</p>
                  <ul className="list-inside list-disc text-sm text-secondary-600 dark:text-secondary-400">
                    {me.notes.map((n, i) => <li key={i}>{n}</li>)}
                  </ul>
                </div>
              )}
            </Section>
          )}

          {/* Profit Analysis */}
          {pa && (
            <Section title="Profit Analysis">
              <div className="grid grid-cols-2 gap-3">
                <InfoItem label="Precio compra" value={formatEur(pa.purchase_price)} />
                <InfoItem label="Coste total" value={formatEur(pa.total_cost)} />
                <InfoItem label="Venta estimada" value={formatEur(pa.estimated_sale_price)} />
                <InfoItem label="Beneficio bruto" value={formatEur(pa.gross_profit)} />
                <InfoItem label="Beneficio neto" value={formatEur(pa.net_profit)} />
                <InfoItem label="ROI" value={`${pa.roi_percentage.toFixed(2)}%`} />
                <InfoItem label="Margen" value={`${pa.profit_margin_percentage.toFixed(2)}%`} />
                <InfoItem label="Riesgo" value={pa.risk_level} />
              </div>

              {/* Cost Breakdown */}
              <div className="mt-3">
                <p className="mb-2 text-sm font-medium text-secondary-700 dark:text-secondary-300">Desglose de costes</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <InfoItem label="Transporte" value={formatEur(pa.cost_breakdown.transport_cost)} />
                  <InfoItem label="Matriculación" value={formatEur(pa.cost_breakdown.registration_cost)} />
                  <InfoItem label="Impuestos" value={formatEur(pa.cost_breakdown.taxes)} />
                  <InfoItem label="Inspección" value={formatEur(pa.cost_breakdown.inspection_cost)} />
                  <InfoItem label="Reparaciones" value={formatEur(pa.cost_breakdown.repair_estimate)} />
                  <InfoItem label="Comisión" value={formatEur(pa.cost_breakdown.commission_cost)} />
                  <InfoItem label="Otros" value={formatEur(pa.cost_breakdown.miscellaneous_cost)} />
                </div>
              </div>
            </Section>
          )}

          {/* Opportunity Analysis */}
          {opp && (
            <Section title="Opportunity Analysis">
              <div className="flex flex-wrap items-center gap-3">
                <ScoreBadge score={Math.round(opp.overall_score)} label="Oportunidad" size="md" />
                <OpportunityBadge level={opp.opportunity_level} size="md" />
                <RecommendationBadge recommendation={opp.recommendation} size="md" />
              </div>
              <div className="mt-3 grid grid-cols-2 gap-3">
                <InfoItem label="Beneficio estimado" value={formatEur(opp.estimated_profit)} />
                <InfoItem label="ROI" value={`${opp.roi.toFixed(2)}%`} />
                <InfoItem label="Confianza mercado" value={`${opp.market_confidence.toFixed(1)}%`} />
                <InfoItem label="Riesgo" value={opp.risk_level} />
              </div>
              {opp.strengths.length > 0 && (
                <div className="mt-2">
                  <p className="mb-1 text-sm font-medium text-green-600 dark:text-green-400">Fortalezas</p>
                  <ul className="list-inside list-disc text-sm text-secondary-600 dark:text-secondary-400">
                    {opp.strengths.map((s, i) => <li key={i}>{s}</li>)}
                  </ul>
                </div>
              )}
              {opp.weaknesses.length > 0 && (
                <div>
                  <p className="mb-1 text-sm font-medium text-red-600 dark:text-red-400">Debilidades</p>
                  <ul className="list-inside list-disc text-sm text-secondary-600 dark:text-secondary-400">
                    {opp.weaknesses.map((w, i) => <li key={i}>{w}</li>)}
                  </ul>
                </div>
              )}
            </Section>
          )}

          {/* Negotiation */}
          {vehicle.negotiation && (
            <Section title="Negociación">
              <div className="flex flex-wrap items-center gap-3">
                <NegotiationBadge recommendation={vehicle.negotiation.recommendation} size="md" />
                {vehicle.negotiation.leverage_score && (
                  <span className="text-sm text-secondary-600 dark:text-secondary-400">
                    Apalancamiento: {vehicle.negotiation.leverage_score.toFixed(0)}/100
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3">
                <InfoItem label="Valor real estimado" value={formatEur(vehicle.negotiation.estimated_vehicle_value)} />
                <InfoItem label="Oferta inicial" value={formatEur(vehicle.negotiation.recommended_initial_offer)} />
                <InfoItem label="Contraoferta" value={formatEur(vehicle.negotiation.recommended_counter_offer)} />
                <InfoItem label="Precio máximo" value={formatEur(vehicle.negotiation.maximum_purchase_price)} />
                <InfoItem label="Precio retirada" value={formatEur(vehicle.negotiation.walk_away_price)} />
                <InfoItem label="Beneficio esperado" value={formatEur(vehicle.negotiation.expected_profit)} />
                <InfoItem label="ROI esperado" value={`${vehicle.negotiation.expected_roi.toFixed(1)}%`} />
                <InfoItem label="Descuento necesario" value={`${vehicle.negotiation.discount_needed.toFixed(1)}%`} />
              </div>

              {/* Argumentos */}
              {vehicle.negotiation.negotiation_arguments.length > 0 && (
                <div>
                  <p className="mb-2 text-sm font-medium text-secondary-700 dark:text-secondary-300">
                    Argumentos de negociación
                  </p>
                  <ol className="list-inside list-decimal space-y-1">
                    {vehicle.negotiation.negotiation_arguments.map((arg, i) => (
                      <li key={i} className="text-xs text-secondary-600 dark:text-secondary-400">
                        <span className="font-medium">{arg.argument}</span>
                        {arg.economic_impact > 0 && (
                          <span className="ml-1 text-red-500">(-{formatEur(arg.economic_impact)})</span>
                        )}
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Script de negociación */}
              {vehicle.negotiation.negotiation_script && (
                <div className="rounded-md bg-secondary-50 p-3 dark:bg-secondary-800">
                  <p className="mb-2 text-sm font-medium text-secondary-700 dark:text-secondary-300">
                    Script de negociación
                  </p>
                  {vehicle.negotiation.negotiation_script.opening && (
                    <div className="mb-2">
                      <p className="text-xs font-medium text-secondary-500">Apertura</p>
                      <p className="text-xs text-secondary-600 dark:text-secondary-400 italic">
                        {`"${vehicle.negotiation.negotiation_script.opening}"`}
                      </p>
                    </div>
                  )}
                  {vehicle.negotiation.negotiation_script.defect_based_points.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs font-medium text-secondary-500">Argumentos (defectos)</p>
                      {vehicle.negotiation.negotiation_script.defect_based_points.map((point, i) => (
                        <p key={i} className="text-xs text-secondary-600 dark:text-secondary-400">{point}</p>
                      ))}
                    </div>
                  )}
                  {vehicle.negotiation.negotiation_script.market_based_points.length > 0 && (
                    <div className="mb-2">
                      <p className="text-xs font-medium text-secondary-500">Argumentos (mercado)</p>
                      {vehicle.negotiation.negotiation_script.market_based_points.map((point, i) => (
                        <p key={i} className="text-xs text-secondary-600 dark:text-secondary-400">{point}</p>
                      ))}
                    </div>
                  )}
                  {vehicle.negotiation.negotiation_script.closing && (
                    <div>
                      <p className="text-xs font-medium text-secondary-500">Cierre</p>
                      <p className="text-xs text-secondary-600 dark:text-secondary-400 italic">
                        {`"${vehicle.negotiation.negotiation_script.closing}"`}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </Section>
          )}

          {/* URL */}
          {vehicle.url && (
            <a
              href={vehicle.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block rounded-lg bg-primary-600 px-4 py-2 text-center text-sm font-medium text-white hover:bg-primary-700"
            >
              Ver anuncio original
            </a>
          )}
        </div>
      </div>
    </>
  );
}

function InfoItem({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <p className="text-xs font-medium text-secondary-500 dark:text-secondary-400">{label}</p>
      <p className="text-sm font-medium text-secondary-900 dark:text-secondary-100">{value || "-"}</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-secondary-200 p-4 dark:border-secondary-700">
      <h3 className="mb-3 text-base font-semibold text-secondary-900 dark:text-secondary-100">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}