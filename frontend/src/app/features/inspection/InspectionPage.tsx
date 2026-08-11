"use client";

import React, { useState, useCallback, useEffect } from "react";
import { inspectionService } from "../../services/inspection";
import { InspectionProgressBar } from "./InspectionProgressBar";
import { CategoryStep } from "./CategoryStep";
import { InspectionSummary } from "./InspectionSummary";
import { LiveNegotiationPanel } from "./LiveNegotiationPanel";
import type {
  InspectionSession,
  InspectionSessionDetail,
  InspectionSummary as InspectionSummaryData,
  CatalogCategory,
  InspectionItemStatus,
  VisionSuggestion,
} from "../../types/inspection";

type PageState = "loading" | "form" | "summary" | "error";

interface InspectionPageProps {
  vehicleId: string;
  sessionId?: string;
  onComplete?: (sessionId: string) => void;
  onBack?: () => void;
}

export function InspectionPage({
  vehicleId,
  sessionId: initialSessionId,
  onComplete,
  onBack,
}: InspectionPageProps) {
  const [pageState, setPageState] = useState<PageState>("loading");
  const [session, setSession] = useState<InspectionSession | null>(null);
  const [catalog, setCatalog] = useState<CatalogCategory[]>([]);
  const [currentCategoryIndex, setCurrentCategoryIndex] = useState(0);
  const [summary, setSummary] = useState<InspectionSummaryData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isUploadingPhoto, setIsUploadingPhoto] = useState(false);
  const [visionSuggestions, setVisionSuggestions] = useState<VisionSuggestion[]>([]);
  const [visionSimulated, setVisionSimulated] = useState<boolean | null>(null);

  // Initialize session
  useEffect(() => {
    async function init() {
      try {
        if (initialSessionId) {
          const detail = await inspectionService.getSession(initialSessionId);
          setSession(detail.session);
          setCatalog(detail.catalog);
          setCurrentCategoryIndex(
            Math.max(0, detail.session.current_category_order - 1),
          );
        } else {
          const newSession = await inspectionService.createSession({
            vehicle_id: vehicleId,
          });
          setSession(newSession);
          // Fetch catalog from the session detail
          const detail = await inspectionService.getSession(newSession.id);
          setCatalog(detail.catalog);
        }
        setPageState("form");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error al iniciar la inspección");
        setPageState("error");
      }
    }
    init();
  }, [vehicleId, initialSessionId]);

  const refreshSummary = useCallback(async () => {
    if (!session || pageState === "summary") return;
    try {
      const fresh = await inspectionService.getSummary(session.id);
      setSummary(fresh);
    } catch (err) {
      console.error("Error refreshing live negotiation:", err);
    }
  }, [session, pageState]);

  const handleItemStatusChange = useCallback(
    async (itemId: string, status: InspectionItemStatus) => {
      if (!session) return;

      const currentCategory = catalog[currentCategoryIndex];
      if (!currentCategory) return;

      // Optimistic update
      setCatalog((prev) =>
        prev.map((cat) =>
          cat.id === currentCategory.id
            ? {
                ...cat,
                items: cat.items.map((item) =>
                  item.id === itemId ? { ...item, status } : item,
                ),
              }
            : cat,
        ),
      );

      try {
        await inspectionService.updateItem(session.id, {
          category_id: currentCategory.id,
          item_id: itemId,
          status,
        });
        await refreshSummary();
      } catch (err) {
        console.error("Error updating item:", err);
        // Revert on error
        setCatalog((prev) =>
          prev.map((cat) =>
            cat.id === currentCategory.id
              ? {
                  ...cat,
                  items: cat.items.map((item) =>
                    item.id === itemId
                      ? { ...item, status: "UNKNOWN" as InspectionItemStatus }
                      : item,
                  ),
                }
              : cat,
          ),
        );
      }
    },
    [session, catalog, currentCategoryIndex, refreshSummary],
  );

  const handleItemNotesChange = useCallback(
    async (itemId: string, notes: string) => {
      if (!session) return;

      const currentCategory = catalog[currentCategoryIndex];
      if (!currentCategory) return;

      setCatalog((prev) =>
        prev.map((cat) =>
          cat.id === currentCategory.id
            ? {
                ...cat,
                items: cat.items.map((item) =>
                  item.id === itemId ? { ...item, notes } : item,
                ),
              }
            : cat,
        ),
      );
    },
    [session, catalog, currentCategoryIndex],
  );

  const handleItemCostChange = useCallback(
    async (itemId: string, cost: number | null) => {
      if (!session) return;

      const currentCategory = catalog[currentCategoryIndex];
      if (!currentCategory) return;

      setCatalog((prev) =>
        prev.map((cat) =>
          cat.id === currentCategory.id
            ? {
                ...cat,
                items: cat.items.map((item) =>
                  item.id === itemId ? { ...item, estimated_repair_cost: cost } : item,
                ),
              }
            : cat,
        ),
      );

      try {
        await inspectionService.updateItem(session.id, {
          category_id: currentCategory.id,
          item_id: itemId,
          status: catalog
            .find((c) => c.id === currentCategory.id)
            ?.items.find((i) => i.id === itemId)?.status ?? "UNKNOWN",
          estimated_repair_cost: cost,
        });
        await refreshSummary();
      } catch (err) {
        console.error("Error updating cost:", err);
      }
    },
    [session, catalog, currentCategoryIndex, refreshSummary],
  );

  const handleNextCategory = useCallback(() => {
    if (currentCategoryIndex < catalog.length - 1) {
      setCurrentCategoryIndex((prev) => prev + 1);
    }
  }, [currentCategoryIndex, catalog.length]);

  const handlePrevCategory = useCallback(() => {
    if (currentCategoryIndex > 0) {
      setCurrentCategoryIndex((prev) => prev - 1);
    }
  }, [currentCategoryIndex]);

  const handleFinalize = useCallback(async () => {
    if (!session) return;
    setIsFinalizing(true);

    try {
      const finalizedSession = await inspectionService.finalizeSession(session.id);
      setSession(finalizedSession);
      const sessionSummary = await inspectionService.getSummary(session.id);
      setSummary(sessionSummary);
      setPageState("summary");
      onComplete?.(session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al finalizar la inspección");
    } finally {
      setIsFinalizing(false);
    }
  }, [session, onComplete]);

  const handleAnalyzePhotos = useCallback(async () => {
    if (!session) return;
    setIsAnalyzing(true);
    try {
      const result = await inspectionService.analyzePhotos(session.id);
      setVisionSuggestions(result.suggestions);
      setVisionSimulated(result.simulated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron analizar las fotografías");
    } finally {
      setIsAnalyzing(false);
    }
  }, [session]);

  const handleSuggestion = useCallback(async (suggestion: VisionSuggestion, accept: boolean) => {
    if (!session) return;
    if (accept) {
      await inspectionService.updateItem(session.id, {
        category_id: suggestion.category_id,
        item_id: suggestion.item_id,
        status: suggestion.status,
        notes: suggestion.notes,
        estimated_repair_cost: suggestion.suggested_repair_cost,
      });
      setCatalog((previous) => previous.map((category) => category.id !== suggestion.category_id ? category : {
        ...category,
        items: category.items.map((item) => item.id !== suggestion.item_id ? item : {
          ...item, status: suggestion.status, severity: suggestion.severity,
          notes: suggestion.notes, estimated_repair_cost: suggestion.suggested_repair_cost,
        }),
      }));
      await refreshSummary();
    }
    setVisionSuggestions((previous) => previous.filter((item) => item.photo_id !== suggestion.photo_id));
  }, [session, refreshSummary]);

  const handleItemPhotoCapture = useCallback(async (itemId: string, _observationId: string | null, file: File) => {
    if (!session) return;

    // Get current category
    const currentCat = catalog[currentCategoryIndex];
    if (!currentCat) return;

    // Find the item
    const item = currentCat.items.find((i) => i.id === itemId);
    if (!item) return;

    setIsUploadingPhoto(true);
    try {
      // If no observation exists yet, first set a status to create one
      if (!item.observation_id) {
        const observation = await inspectionService.updateItem(session.id, {
          category_id: currentCat.id,
          item_id: itemId,
          status: "UNKNOWN",
        });
        // Update catalog with observation_id
        setCatalog((prev) =>
          prev.map((cat) =>
            cat.id === currentCat.id
              ? {
                  ...cat,
                  items: cat.items.map((i) =>
                    i.id === itemId ? { ...i, observation_id: observation.id } : i,
                  ),
                }
              : cat,
          ),
        );
        // Upload photo with new observation_id
        await inspectionService.uploadPhotoFile(session.id, observation.id, file);
      } else {
        // Upload photo with existing observation_id
        await inspectionService.uploadPhotoFile(session.id, item.observation_id, file);
      }
      await refreshSummary();
    } catch (err) {
      console.error("Error uploading photo:", err);
      setError(err instanceof Error ? err.message : "Error al subir fotografía");
    } finally {
      setIsUploadingPhoto(false);
    }
  }, [session, catalog, currentCategoryIndex, refreshSummary]);

  const currentCategory = catalog[currentCategoryIndex];
  const totalItems = catalog.reduce((sum, cat) => sum + cat.items.length, 0);
  const reviewedItems = catalog.reduce(
    (sum, cat) =>
      sum + cat.items.filter((item) => item.status !== "UNKNOWN").length,
    0,
  );

  if (pageState === "loading") {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  if (pageState === "error") {
    return (
      <div className="rounded-lg bg-red-50 p-6 text-center">
        <p className="text-red-800">{error || "Error desconocido"}</p>
        {onBack && (
          <button
            onClick={onBack}
            className="mt-4 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
          >
            Volver
          </button>
        )}
      </div>
    );
  }

  if (pageState === "summary" && summary) {
    return (
      <InspectionSummary
        summary={summary}
        onNewInspection={onBack}
      />
    );
  }

  if (!currentCategory || !session) {
    return (
      <div className="rounded-lg bg-yellow-50 p-6 text-center">
        <p className="text-yellow-800">No hay categorías de inspección disponibles.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            Inspección de vehículo
          </h1>
          <p className="text-sm text-gray-500">
            Sesión: {session.id.slice(0, 8)}...
          </p>
        </div>
        {onBack && (
          <button
            onClick={onBack}
            className="rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Cancelar
          </button>
        )}
      </div>

      <InspectionProgressBar
        currentStep={currentCategoryIndex + 1}
        totalSteps={catalog.length}
        reviewedItems={reviewedItems}
        totalItems={totalItems}
      />

      {summary?.negotiation && (
        <LiveNegotiationPanel
          totalRepairCost={summary.costs?.total_repair_cost ?? 0}
          negotiation={summary.negotiation}
        />
      )}

      <div className="rounded-lg border border-gray-200 p-4">
        <button
          onClick={handleAnalyzePhotos}
          disabled={isAnalyzing}
          className="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700 disabled:opacity-50"
        >
          {isAnalyzing ? "Analizando fotografías..." : "Analizar fotografías"}
        </button>
        {visionSimulated && (
          <div className="mt-3 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
            <p className="font-medium">Análisis simulado (Mock)</p>
            <p className="mt-1">
              No hay <code>GEMINI_API_KEY</code> ni <code>OPENAI_API_KEY</code> configuradas.
              Las sugerencias mostradas son genéricas e inventadas: revísalas manualmente
              y no las trates como una inspección real.
            </p>
          </div>
        )}
        {visionSuggestions.length > 0 && (
          <div className="mt-4 space-y-3">
            <p className="text-sm font-medium text-gray-800">Sugerencias (no aplicadas)</p>
            {visionSuggestions.map((suggestion) => (
              <div key={suggestion.photo_id} className="rounded-md bg-violet-50 p-3 text-sm text-gray-700">
                <p>{suggestion.notes}</p>
                <p className="mt-1">Estado sugerido: {suggestion.status} · Confianza: {suggestion.confidence}</p>
                <div className="mt-2 flex gap-2">
                  <button onClick={() => handleSuggestion(suggestion, true)} className="rounded bg-green-600 px-3 py-1 text-white">Aceptar</button>
                  <button onClick={() => handleSuggestion(suggestion, false)} className="rounded border border-gray-300 bg-white px-3 py-1">Rechazar</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <CategoryStep
        category={currentCategory}
        onItemStatusChange={handleItemStatusChange}
        onItemNotesChange={handleItemNotesChange}
        onItemCostChange={handleItemCostChange}
        onItemPhotoCapture={handleItemPhotoCapture}
      />

      <div className="flex items-center justify-between border-t pt-4">
        <div>
          {currentCategoryIndex > 0 && (
            <button
              onClick={handlePrevCategory}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Anterior
            </button>
          )}
        </div>

        <div className="flex gap-3">
          {currentCategoryIndex === catalog.length - 1 ? (
            <button
              onClick={handleFinalize}
              disabled={isFinalizing}
              className="rounded-md bg-green-600 px-6 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
            >
              {isFinalizing ? "Finalizando..." : "Finalizar inspección"}
            </button>
          ) : (
            <button
              onClick={handleNextCategory}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Siguiente categoría
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
