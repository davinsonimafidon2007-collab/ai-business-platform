"use client";

import React, { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { InspectionPage } from "@/app/features/inspection/InspectionPage";

function InspectionRouteContent() {
  const searchParams = useSearchParams();
  const vehicleIdFromUrl = searchParams.get("vehicle_id");
  const [vehicleId, setVehicleId] = useState<string | null>(vehicleIdFromUrl);
  const [showForm, setShowForm] = useState(!!vehicleIdFromUrl);

  if (!showForm) {
    return (
      <div className="mx-auto max-w-4xl py-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-secondary-900 dark:text-secondary-100">
            Inspección de Vehículos
          </h1>
          <p className="mt-2 text-secondary-600 dark:text-secondary-400">
            Seleccione un vehículo desde la sección de búsqueda para iniciar una
            inspección, o ingrese manualmente el ID del vehículo.
          </p>
        </div>

        <div className="rounded-lg bg-white p-8 shadow dark:bg-secondary-900 dark:shadow-none dark:ring-1 dark:ring-primary-900/20">
          <h2 className="text-lg font-semibold text-secondary-900 dark:text-secondary-100">
            Iniciar nueva inspección
          </h2>
          <p className="mt-2 text-sm text-secondary-500 dark:text-secondary-400">
            Ingrese el ID del vehículo que desea inspeccionar.
          </p>

          <div className="mt-4 flex gap-3">
            <input
              type="text"
              placeholder="ID del vehículo"
              value={vehicleId ?? ""}
              onChange={(e) => setVehicleId(e.target.value)}
              className="block flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500 dark:border-secondary-600 dark:bg-secondary-800 dark:text-secondary-100"
            />
            <button
              onClick={() => vehicleId && setShowForm(true)}
              disabled={!vehicleId}
              className="rounded-md bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-500 disabled:opacity-50"
            >
              Comenzar
            </button>
          </div>
        </div>

        <div className="mt-6 rounded-lg bg-blue-50 p-4 dark:bg-primary-950/40 dark:ring-1 dark:ring-primary-900/30">
          <h3 className="text-sm font-medium text-blue-800 dark:text-primary-200">
            ¿Cómo funciona?
          </h3>
          <ul className="mt-2 list-inside list-disc text-sm text-blue-700 dark:text-primary-300">
            <li>Seleccione el vehículo a inspeccionar por su ID</li>
            <li>Revise cada categoría (Exterior, Interior, Motor, etc.)</li>
            <li>Marque el estado de cada punto de inspección</li>
            <li>Añada notas y costes estimados de reparación</li>
            <li>Finalice la inspección para ver el resumen completo</li>
          </ul>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl py-8">
      <InspectionPage
        vehicleId={vehicleId!}
        onBack={() => {
          setShowForm(false);
          setVehicleId(null);
        }}
      />
    </div>
  );
}

export default function InspectionRoute() {
  return (
    <Suspense fallback={null}>
      <InspectionRouteContent />
    </Suspense>
  );
}