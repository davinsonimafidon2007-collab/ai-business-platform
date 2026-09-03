"use client";

import React from "react";

interface InspectionProgressBarProps {
  currentStep: number;
  totalSteps: number;
  reviewedItems: number;
  totalItems: number;
}

export function InspectionProgressBar({
  currentStep,
  totalSteps,
  reviewedItems,
  totalItems,
}: InspectionProgressBarProps) {
  const stepPercentage = totalSteps > 0 ? ((currentStep) / totalSteps) * 100 : 0;
  const itemPercentage = totalItems > 0 ? (reviewedItems / totalItems) * 100 : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm text-secondary-600 dark:text-secondary-400">
        <span>
          Paso {currentStep} de {totalSteps}
        </span>
        <span>
          {reviewedItems} / {totalItems} revisados
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-gray-200 dark:bg-secondary-800">
        <div
          className="h-full rounded-full bg-primary-500 transition-all duration-300"
          style={{ width: `${Math.max(stepPercentage, itemPercentage)}%` }}
        />
      </div>
    </div>
  );
}
