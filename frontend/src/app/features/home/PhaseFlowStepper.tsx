"use client";

import { Car, FileText, Truck, ClipboardCheck, Tag, type LucideIcon } from "lucide-react";

export type PhaseFlowStep = {
  key: string;
  label: string;
  count: number;
};

const ICONS: LucideIcon[] = [Car, FileText, Truck, ClipboardCheck, Tag];

const TONE_CLASSES = [
  "bg-emerald-500/20 text-emerald-500",
  "bg-sky-500/20 text-sky-500",
  "bg-amber-500/20 text-amber-500",
  "bg-primary-500/20 text-primary-400",
  "bg-secondary-500/20 text-secondary-400",
];

/** Resumen visual del pipeline de deals agrupado en 5 etapas de negocio
 * (Búsqueda/Documentación/Traslado/Matriculación/Venta), derivado del
 * desglose real por estado de GET /deals/reports/portfolio — no son
 * conteos inventados, solo una agrupación distinta de datos reales. */
export function PhaseFlowStepper({ steps }: { steps: PhaseFlowStep[] }) {
  return (
    <div className="overflow-x-auto">
      <div className="flex min-w-max items-start gap-1 px-1 py-2">
        {steps.map((step, i) => {
          const Icon = ICONS[i % ICONS.length];
          const tone = TONE_CLASSES[i % TONE_CLASSES.length];
          return (
            <div key={step.key} className="flex items-start">
              <div className="flex w-24 flex-col items-center text-center">
                <span
                  className={`flex h-12 w-12 items-center justify-center rounded-full text-lg font-semibold ${tone}`}
                >
                  <Icon className="h-5 w-5" aria-hidden />
                </span>
                <p className="mt-2 text-lg font-bold text-secondary-900 dark:text-primary-50">
                  {step.count}
                </p>
                <p className="text-xs font-medium text-secondary-700 dark:text-secondary-300">
                  {step.label}
                </p>
                <p className="text-[10px] text-secondary-400">
                  {step.count === 1 ? "1 activa" : `${step.count} activas`}
                </p>
              </div>
              {i < steps.length - 1 && (
                <div
                  className="mt-6 h-px w-8 border-t border-dashed border-secondary-300 dark:border-secondary-700"
                  aria-hidden
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
