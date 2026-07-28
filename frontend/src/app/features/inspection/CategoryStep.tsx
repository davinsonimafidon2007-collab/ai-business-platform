"use client";

import React from "react";
import type { CatalogCategory, InspectionItemStatus } from "../../types/inspection";

interface CategoryStepProps {
  category: CatalogCategory;
  onItemStatusChange: (itemId: string, status: InspectionItemStatus) => void;
  onItemNotesChange: (itemId: string, notes: string) => void;
  onItemCostChange: (itemId: string, cost: number | null) => void;
}

const STATUS_OPTIONS: { value: InspectionItemStatus; label: string; color: string }[] = [
  { value: "GOOD", label: "Bueno", color: "bg-green-100 text-green-800 border-green-300" },
  { value: "WARNING", label: "Advertencia", color: "bg-yellow-100 text-yellow-800 border-yellow-300" },
  { value: "BAD", label: "Defectuoso", color: "bg-red-100 text-red-800 border-red-300" },
  { value: "UNKNOWN", label: "Sin revisar", color: "bg-gray-100 text-gray-800 border-gray-300" },
];

export function CategoryStep({
  category,
  onItemStatusChange,
  onItemNotesChange,
  onItemCostChange,
}: CategoryStepProps) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-2xl">{category.icon}</span>
        <div>
          <h2 className="text-lg font-semibold text-gray-900">{category.label}</h2>
          {category.description && (
            <p className="text-sm text-gray-500">{category.description}</p>
          )}
        </div>
      </div>

      <div className="space-y-3">
        {category.items.map((item) => (
          <div
            key={item.id}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-medium text-gray-900">{item.label}</h3>
                {item.description && (
                  <p className="mt-1 text-sm text-gray-500">{item.description}</p>
                )}
                {item.is_safety_relevant && (
                  <span className="mt-1 inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
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
                      : "border-gray-200 bg-white text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>

            {item.has_cost_estimate && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700">
                  Coste estimado de reparación (€)
                </label>
                <input
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
                  className="mt-1 block w-48 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="0.00"
                />
              </div>
            )}

            {item.allows_photos && (
              <div className="mt-3">
                <label className="block text-sm font-medium text-gray-700">
                  Notas
                </label>
                <textarea
                  value={item.notes ?? ""}
                  onChange={(e) => onItemNotesChange(item.id, e.target.value)}
                  rows={2}
                  className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
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
