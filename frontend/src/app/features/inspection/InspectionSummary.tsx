"use client";

import React from "react";
import type { InspectionSummary as InspectionSummaryData } from "../../types/inspection";

interface InspectionSummaryProps {
  summary: InspectionSummaryData;
  onExport?: () => void;
  onNewInspection?: () => void;
}

function getRiskLevelColor(level: string): string {
  switch (level.toLowerCase()) {
    case "critical":
    case "high":
      return "bg-red-100 text-red-800";
    case "medium":
      return "bg-yellow-100 text-yellow-800";
    case "low":
      return "bg-green-100 text-green-800";
    default:
      return "bg-gray-100 text-gray-800";
  }
}

function getConditionColor(condition: number | null): string {
  if (condition === null) return "bg-gray-100 text-gray-800";
  if (condition >= 8) return "bg-green-100 text-green-800";
  if (condition >= 5) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

export function InspectionSummary({
  summary,
  onExport,
  onNewInspection,
}: InspectionSummaryProps) {
  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-white p-6 shadow">
        <h2 className="text-xl font-semibold text-gray-900">Resumen de Inspección</h2>

        <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-sm text-gray-500">Estado general</p>
            <p
              className={`mt-1 inline-block rounded-full px-2 py-0.5 text-sm font-medium ${getConditionColor(summary.overall_condition)}`}
            >
              {summary.overall_condition !== null
                ? `${summary.overall_condition}/10`
                : "N/A"}
            </p>
          </div>

          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-sm text-gray-500">Riesgo</p>
            <p
              className={`mt-1 inline-block rounded-full px-2 py-0.5 text-sm font-medium ${getRiskLevelColor(summary.risk_level)}`}
            >
              {summary.risk_level}
            </p>
          </div>

          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-sm text-gray-500">Defectos totales</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {summary.defects.total}
            </p>
          </div>

          <div className="rounded-lg bg-gray-50 p-3">
            <p className="text-sm text-gray-500">Coste reparación</p>
            <p className="mt-1 text-lg font-semibold text-gray-900">
              {summary.costs.total_repair_cost.toFixed(2)} €
            </p>
          </div>
        </div>

        <div className="mt-4">
          <p className="text-sm text-gray-500">Recomendación</p>
          <p className="mt-1 text-gray-900">{summary.recommendation}</p>
        </div>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="text-lg font-semibold text-gray-900">
          Desglose de defectos
        </h3>

        <div className="mt-3 grid grid-cols-3 gap-3">
          <div className="rounded-lg bg-green-50 p-3 text-center">
            <p className="text-2xl font-bold text-green-600">{summary.defects.good}</p>
            <p className="text-sm text-green-700">Correctos</p>
          </div>
          <div className="rounded-lg bg-yellow-50 p-3 text-center">
            <p className="text-2xl font-bold text-yellow-600">
              {summary.defects.warning}
            </p>
            <p className="text-sm text-yellow-700">Advertencias</p>
          </div>
          <div className="rounded-lg bg-red-50 p-3 text-center">
            <p className="text-2xl font-bold text-red-600">{summary.defects.bad}</p>
            <p className="text-sm text-red-700">Defectos</p>
          </div>
        </div>

        <div className="mt-4">
          <h4 className="font-medium text-gray-700">Defectos críticos</h4>
          <p className="text-2xl font-bold text-red-600">
            {summary.defects.critical}
          </p>
        </div>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="text-lg font-semibold text-gray-900">
          Desglose de costes
        </h3>
        <div className="mt-3 space-y-2">
          <div className="flex justify-between">
            <span className="text-gray-600">Piezas</span>
            <span className="font-medium">
              {summary.costs.parts_cost.toFixed(2)} €
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Mano de obra</span>
            <span className="font-medium">
              {summary.costs.labor_cost.toFixed(2)} €
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-600">Pintura y carrocería</span>
            <span className="font-medium">
              {summary.costs.paint_and_body_cost.toFixed(2)} €
            </span>
          </div>
          <hr />
          <div className="flex justify-between text-lg font-semibold">
            <span>Total</span>
            <span>{summary.costs.total_repair_cost.toFixed(2)} €</span>
          </div>
        </div>
      </div>

      <div className="rounded-lg bg-white p-6 shadow">
        <h3 className="text-lg font-semibold text-gray-900">
          Progreso de revisión
        </h3>
        <div className="mt-3">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              Revisados: {summary.progress.reviewed_items} /{" "}
              {summary.progress.total_items}
            </span>
            <span>{summary.progress.percentage.toFixed(0)}%</span>
          </div>
          <div className="mt-2 h-2 w-full rounded-full bg-gray-200">
            <div
              className="h-full rounded-full bg-blue-500 transition-all"
              style={{ width: `${summary.progress.percentage}%` }}
            />
          </div>
        </div>
      </div>

      {summary.negotiation && (
        <div className="rounded-lg bg-white p-6 shadow">
          <h3 className="text-lg font-semibold text-gray-900">Estrategia de Negociación</h3>

          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg bg-blue-50 p-3">
              <p className="text-sm text-gray-500">Valor estimado</p>
              <p className="mt-1 text-lg font-bold text-blue-700">{summary.negotiation.estimated_vehicle_value.toFixed(0)} €</p>
            </div>
            <div className="rounded-lg bg-green-50 p-3">
              <p className="text-sm text-gray-500">Oferta inicial</p>
              <p className="mt-1 text-lg font-bold text-green-700">{summary.negotiation.recommended_initial_offer.toFixed(0)} €</p>
            </div>
            <div className="rounded-lg bg-orange-50 p-3">
              <p className="text-sm text-gray-500">Precio máximo</p>
              <p className="mt-1 text-lg font-bold text-orange-700">{summary.negotiation.maximum_purchase_price.toFixed(0)} €</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3">
              <p className="text-sm text-gray-500">Walk-away price</p>
              <p className="mt-1 text-lg font-bold text-red-700">{summary.negotiation.walk_away_price.toFixed(0)} €</p>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-sm text-gray-500">Beneficio estimado</p>
              <p className={`mt-1 text-lg font-bold ${summary.negotiation.expected_profit >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                {summary.negotiation.expected_profit.toFixed(0)} €
              </p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-sm text-gray-500">ROI estimado</p>
              <p className="mt-1 text-lg font-bold text-gray-900">{summary.negotiation.expected_roi.toFixed(1)}%</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-sm text-gray-500">Apalancamiento</p>
              <p className="mt-1 text-lg font-bold text-gray-900">{summary.negotiation.leverage_score.toFixed(0)}/100</p>
            </div>
            <div className="rounded-lg bg-gray-50 p-3">
              <p className="text-sm text-gray-500">Descuento necesario</p>
              <p className="mt-1 text-lg font-bold text-gray-900">{summary.negotiation.discount_needed.toFixed(1)}%</p>
            </div>
          </div>

          <div className="mt-4">
            <p className="text-sm text-gray-500">Recomendación</p>
            <p className={`mt-1 inline-block rounded-full px-3 py-1 text-sm font-bold ${
              summary.negotiation.recommendation === 'BUY' ? 'bg-green-100 text-green-800' :
              summary.negotiation.recommendation === 'NEGOTIATE' ? 'bg-yellow-100 text-yellow-800' :
              'bg-red-100 text-red-800'
            }`}>
              {summary.negotiation.recommendation === 'BUY' ? 'COMPRAR' :
               summary.negotiation.recommendation === 'NEGOTIATE' ? 'NEGOCIAR' :
               'ABANDONAR'}
            </p>
          </div>

          {summary.negotiation.negotiation_arguments.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-gray-700">Argumentos principales</p>
              <ul className="mt-2 space-y-1">
                {summary.negotiation.negotiation_arguments.slice(0, 5).map((arg, i) => (
                  <li key={i} className="rounded-md bg-gray-50 p-2 text-sm text-gray-700">
                    <span className="font-medium text-gray-900">{arg.argument}</span>
                    <span className="ml-2 text-blue-600">({arg.economic_impact.toFixed(0)} €)</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {summary.negotiation.negotiation_script.opening && (
            <div className="mt-4">
              <p className="text-sm font-medium text-gray-700">Guión de negociación</p>
              <details className="mt-2">
                <summary className="cursor-pointer text-sm text-blue-600 hover:text-blue-800">Ver guión completo</summary>
                <div className="mt-2 space-y-2 rounded-md bg-gray-50 p-3 text-sm text-gray-700">
                  <p><span className="font-medium">Apertura:</span> {summary.negotiation.negotiation_script.opening}</p>
                  {summary.negotiation.negotiation_script.defect_based_points.length > 0 && (
                    <div>
                      <p className="font-medium">Puntos por defectos:</p>
                      <ul className="ml-4 list-disc">
                        {summary.negotiation.negotiation_script.defect_based_points.map((point, i) => (
                          <li key={i}>{point}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {summary.negotiation.negotiation_script.market_based_points.length > 0 && (
                    <div>
                      <p className="font-medium">Puntos de mercado:</p>
                      <ul className="ml-4 list-disc">
                        {summary.negotiation.negotiation_script.market_based_points.map((point, i) => (
                          <li key={i}>{point}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <p><span className="font-medium">Cierre:</span> {summary.negotiation.negotiation_script.closing}</p>
                </div>
              </details>
            </div>
          )}
        </div>
      )}

      {(onExport || onNewInspection) && (
        <div className="flex gap-3">
          {onExport && (
            <button
              onClick={onExport}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Exportar resumen
            </button>
          )}
          {onNewInspection && (
            <button
              onClick={onNewInspection}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Nueva inspección
            </button>
          )}
        </div>
      )}
    </div>
  );
}
