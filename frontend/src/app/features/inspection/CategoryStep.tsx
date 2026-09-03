"use client";

import React from "react";
import type { CatalogCategory, InspectionItemStatus } from "../../types/inspection";

interface CategoryStepProps {
  category: CatalogCategory;
  onItemStatusChange: (itemId: string, status: InspectionItemStatus) => void;
  onItemNotesChange: (itemId: string, notes: string) => void;
  onItemCostChange: (itemId: string, cost: number | null) => void;
  onItemPhotoCapture?: (itemId: string, observationId: string | null, file: File) => void;
}

const STATUS_OPTIONS: { value: InspectionItemStatus; label: string; color: string }[] = [
  { value: "GOOD", label: "Bueno", color: "bg-green-100 text-green-800 border-green-300 dark:bg-green-900/30 dark:text-green-300 dark:border-green-700/50" },
  { value: "WARNING", label: "Advertencia", color: "bg-yellow-100 text-yellow-800 border-yellow-300 dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-700/50" },
  { value: "BAD", label: "Defectuoso", color: "bg-red-100 text-red-800 border-red-300 dark:bg-red-900/30 dark:text-red-300 dark:border-red-700/50" },
  { value: "UNKNOWN", label: "Sin revisar", color: "bg-gray-100 text-gray-800 border-gray-300 dark:bg-secondary-800 dark:text-secondary-300 dark:border-secondary-600" },
];

export function CategoryStep({
  category,
  onItemStatusChange,
  onItemNotesChange,
  onItemCostChange,
  onItemPhotoCapture,
}: CategoryStepProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-2xl">{category.icon}</span>
        <div>
          <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">{category.label}</h2>
          {category.description && (
            <p className="text-sm text-secondary-500 dark:text-secondary-400">{category.description}</p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {category.items.map((item) => (
          <div
            key={item.id}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-secondary-700 dark:bg-secondary-900 dark:shadow-none"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-medium text-secondary-900 dark:text-secondary-100">{item.label}</h3>
                {item.description && (
                  <p className="mt-1 text-sm text-secondary-500 dark:text-secondary-400">{item.description}</p>
                )}
                {item.is_safety_relevant && (
                  <span className="mt-1 inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-300">
                    Seguridad
                  </span>
                )}
              </div>
            </div>

            <div className="mt-3 flex flex-wrap gap-2">
              {STATUS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => onItemStatusChange(item.id, opt.value)}
                  className={`rounded-md border px-3 py-1 text-sm font-medium transition-colors ${
                    item.status === opt.value
                      ? opt.color
                      : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50 dark:border-secondary-600 dark:bg-secondary-800 dark:text-secondary-300 dark:hover:bg-secondary-700"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {item.has_cost_estimate && (
              <div className="mt-3">
                <label htmlFor={`cost-${item.id}`} className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">
                  Coste estimado de reparación (€)
                </label>
                <input
                  id={`cost-${item.id}`}
                  type="number"
                  min="0"
                  step="0.01"
                  value={item.estimated_repair_cost ?? ""}
                  onChange={(e) =>
                    onItemCostChange(
                      item.id,
                      e.target.value ? parseFloat(e.target.value) : null,
                    )
                  }
                  className="mt-1 block w-48 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-secondary-600 dark:bg-secondary-800 dark:text-secondary-100"
                  placeholder="0.00"
                />
              </div>
            )}

            {item.allows_photos && (
              <div className="mt-3 space-y-2">
                <div className="flex items-center gap-2">
                  <label htmlFor={`photo-${item.id}`} className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">
                    Fotografía
                  </label>
                  <input
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    id={`photo-${item.id}`}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file && onItemPhotoCapture) {
                        onItemPhotoCapture(item.id, item.observation_id, file);
                      }
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      const input = document.getElementById(`photo-${item.id}`) as HTMLInputElement;
                      if (input) input.click();
                    }}
                    className="inline-flex items-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-sm font-medium text-blue-700 hover:bg-blue-100 dark:bg-primary-900/30 dark:text-primary-300 dark:hover:bg-primary-900/50"
                  >
                    📷 Añadir fotografía
                  </button>
                </div>
                <label htmlFor={`notes-${item.id}`} className="block text-sm font-medium text-secondary-700 dark:text-secondary-300">
                  Notas
                </label>
                <textarea
                  id={`notes-${item.id}`}
                  value={item.notes ?? ""}
                  onChange={(e) => onItemNotesChange(item.id, e.target.value)}
                  rows={2}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-secondary-600 dark:bg-secondary-800 dark:text-secondary-100"
                  placeholder="Observaciones adicionales..."
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
