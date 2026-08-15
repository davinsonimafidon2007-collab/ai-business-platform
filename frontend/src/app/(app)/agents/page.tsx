"use client";

import { useState, useMemo } from "react";
import { useAgents } from "@/app/hooks/useAgents";
import { AgentCard } from "@/app/components/agents/AgentCard";
import { Skeleton } from "@/app/components/ui/Skeleton";
import { ErrorDisplay } from "@/app/components/ui/ErrorDisplay";
import { EmptyState } from "@/app/components/ui/EmptyState";
import { Search, Plus } from "lucide-react";

export default function AgentsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const { data, isLoading, isError, refetch } = useAgents();

  const agentsList = useMemo(() => data ?? [], [data]);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return agentsList;
    const q = searchQuery.toLowerCase();
    return agentsList.filter(
      (a: any) =>
        a.name?.toLowerCase().includes(q) ||
        a.role?.toLowerCase().includes(q) ||
        a.description?.toLowerCase().includes(q)
    );
  }, [agentsList, searchQuery]);

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Agentes</h1>
          <p className="text-sm text-secondary-500 mt-0.5">
            {isLoading ? "Cargando..." : `${filtered.length} agentes disponibles`}
          </p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-sm font-semibold transition-colors active:scale-95">
          <Plus className="w-4 h-4" />
          <span className="hidden sm:inline">Nuevo agente</span>
        </button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-600" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Buscar agente..."
          className="w-full h-10 pl-10 pr-4 rounded-xl bg-[#16161f] border border-[#1e1e2d] text-sm text-white placeholder:text-secondary-600 focus:outline-none focus:border-primary-600 focus:ring-1 focus:ring-primary-600/30 transition-all"
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="p-4 rounded-2xl bg-[#111118] border border-[#1e1e2d] space-y-4">
              <div className="flex items-center gap-3">
                <Skeleton className="w-11 h-11 rounded-xl" />
                <div className="space-y-2">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
              </div>
              <Skeleton className="h-3 w-full" />
              <div className="grid grid-cols-3 gap-2">
                <Skeleton className="h-12 rounded-xl" />
                <Skeleton className="h-12 rounded-xl" />
                <Skeleton className="h-12 rounded-xl" />
              </div>
            </div>
          ))}
        </div>
      ) : isError ? (
        <ErrorDisplay
          title="Error al cargar agentes"
          message="No se pudieron obtener los agentes."
          onRetry={refetch}
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Search}
          title="Sin resultados"
          description={searchQuery ? `No se encontraron agentes para "${searchQuery}"` : "No hay agentes configurados."}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {filtered.map((agent: any) => (
            <AgentCard
              key={agent.id || agent.name}
              name={agent.name}
              role={agent.role}
              description={agent.description}
              status={agent.status || "idle"}
              tasksCompleted={agent.tasks_completed || 0}
              avgTime={agent.avg_time || "0m"}
              successRate={agent.success_rate || 0}
            />
          ))}
        </div>
      )}
    </div>
  );
}
