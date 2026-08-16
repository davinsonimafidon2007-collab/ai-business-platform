"use client";

import { useState, useMemo } from "react";
import { useWorkflows } from "@/app/hooks/useWorkflows";
import { WorkflowCard } from "@/app/components/workflows/WorkflowCard";
import { Skeleton } from "@/app/components/ui/Skeleton";
import { ErrorDisplay } from "@/app/components/ui/ErrorDisplay";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { Search, Plus, SlidersHorizontal } from "lucide-react";

const FILTERS = ["Todos", "En ejecución", "Completados", "Pausados", "Fallidos"] as const;
type FilterType = (typeof FILTERS)[number];

const STATUS_MAP: Record<string, string> = {
  "En ejecución": "running",
  Completados: "completed",
  Pausados: "paused",
  Fallidos: "failed",
};

export default function WorkflowsPage() {
  const [activeFilter, setActiveFilter] = useState<FilterType>("Todos");
  const [searchQuery, setSearchQuery] = useState("");
  const { data, isLoading, isError, refetch } = useWorkflows();

  const workflowsList = useMemo(() => data ?? [], [data]);

  const filtered = useMemo(() => {
    let result = workflowsList;
    if (activeFilter !== "Todos") {
      result = result.filter((w: any) => w.status === STATUS_MAP[activeFilter]);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (w: any) =>
          w.name?.toLowerCase().includes(q) ||
          w.description?.toLowerCase().includes(q)
      );
    }
    return result;
  }, [workflowsList, activeFilter, searchQuery]);

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Workflows</h1>
          <p className="text-sm text-secondary-500 mt-0.5">
            {isLoading ? "Cargando..." : `${filtered.length} workflows`}
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-semibold transition-colors active:scale-95">
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Nuevo workflow</span>
        </button>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-600" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Buscar workflow..."
            className="w-full h-10 pl-10 pr-4 rounded-xl bg-[#16161f] border border-[#1e1e2d] text-sm text-white placeholder:text-secondary-600 focus:outline-none focus:border-primary-600 focus:ring-1 focus:ring-primary-600/30 transition-all"
          />
        </div>
        <button className="flex items-center justify-center gap-2 h-10 px-4 rounded-xl bg-[#16161f] border border-[#1e1e2d] text-secondary-300 hover:text-white text-sm font-medium transition-colors">
          <SlidersHorizontal className="w-4 h-4" />
          <span className="hidden sm:inline">Filtros</span>
        </button>
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 lg:mx-0 lg:px-0 scrollbar-hide">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setActiveFilter(f)}
            className={`px-3.5 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
              activeFilter === f
                ? "bg-primary-600 text-white"
                : "bg-[#16161f] border border-[#1e1e2d] text-secondary-400 hover:text-white hover:border-[#2a2a3d]"
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="p-4 rounded-2xl bg-[#111118] border border-[#1e1e2d] space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Skeleton className="w-10 h-10 rounded-xl" />
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-20" />
                  </div>
                </div>
                <Skeleton className="h-6 w-20 rounded-md" />
              </div>
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-1.5 w-full rounded-full" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <ErrorDisplay
          title="Error al cargar workflows"
          message="No se pudieron obtener los workflows."
          onRetry={refetch}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Search}
          title="Sin resultados"
          description={searchQuery ? `No se encontraron workflows para "${searchQuery}"` : "No hay workflows configurados."}
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((wf: any) => (
            <WorkflowCard
              key={wf.id}
              id={wf.id}
              name={wf.name}
              description={wf.description}
              status={wf.status || "paused"}
              phases={wf.phases || 5}
              completedPhases={wf.completed_phases || 0}
              lastRun={wf.last_run || "Hace 1 d"}
            />
          ))}
        </div>
      )}
    </div>
  );
}
