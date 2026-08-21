"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useOpportunities } from "@/app/hooks/useOpportunities";
import { OpportunityCard } from "@/app/components/opportunities/OpportunityCard";
import { SkeletonCard, ErrorState, EmptyState } from "@/components/ui/StateComponents";
import { Pagination } from "@/app/components/ui/Pagination";
import { Search, SlidersHorizontal } from "lucide-react";

const FILTERS = ["Todas", "Activas", "Pendientes", "Completadas", "Abortadas"] as const;
type FilterType = (typeof FILTERS)[number];

const STATUS_MAP: Record<string, string> = {
  Activas: "active",
  Pendientes: "pending",
  Completadas: "completed",
  Abortadas: "aborted",
};

const ITEMS_PER_PAGE = 5;

export default function OpportunitiesPage() {
  const router = useRouter();
  const [activeFilter, setActiveFilter] = useState<FilterType>("Todas");
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);

  const { data, isLoading, isError, refetch } = useOpportunities({
    limit: 50,
    status: activeFilter !== "Todas" ? STATUS_MAP[activeFilter] : undefined,
  });

  const allItemsList = useMemo(() => data?.items ?? [], [data]);

  const filtered = useMemo(() => {
    if (!searchQuery.trim()) return allItemsList;
    const q = searchQuery.toLowerCase();
    return allItemsList.filter(
      (o: any) =>
        o.vehicle?.brand?.toLowerCase().includes(q) ||
        o.vehicle?.model?.toLowerCase().includes(q)
    );
  }, [allItemsList, searchQuery]);

  const totalPages = Math.ceil(filtered.length / ITEMS_PER_PAGE);
  const paginated = filtered.slice(
    (currentPage - 1) * ITEMS_PER_PAGE,
    currentPage * ITEMS_PER_PAGE
  );

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white">Oportunidades</h1>
          <p className="text-sm text-secondary-500 mt-0.5">
            {isLoading ? "Cargando..." : `${filtered.length} en total`}
          </p>
        </div>
      </div>

      {/* Search + Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-secondary-600" aria-hidden="true" />
          <input
            type="text"
            id="opportunity-search"
            aria-label="Buscar oportunidad"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Buscar oportunidad..."
            className="w-full h-10 pl-10 pr-4 rounded-xl bg-[#16161f] border border-[#1e1e2d] text-sm text-white placeholder:text-secondary-600 focus:outline-none focus:border-primary-600 focus:ring-1 focus:ring-primary-600/30 transition-all"
          />
        </div>
        <button
          className="flex items-center justify-center gap-2 h-10 px-4 rounded-xl bg-[#16161f] border border-[#1e1e2d] text-secondary-300 hover:text-white text-sm font-medium transition-colors"
          aria-label="Filtrar oportunidades"
        >
          <SlidersHorizontal className="w-4 h-4" aria-hidden="true" />
          <span className="hidden sm:inline">Filtros</span>
        </button>
      </div>

      {/* Filter chips */}
      <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4 lg:mx-0 lg:px-0 scrollbar-hide">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => {
              setActiveFilter(f);
              setCurrentPage(1);
            }}
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

      {/* Content */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} lines={3} />
          ))}
        </div>
      ) : isError ? (
        <ErrorState
          title="Error al cargar oportunidades"
          message="No se pudieron obtener las oportunidades. Verifica tu conexión."
          onRetry={refetch}
        />
      ) : paginated.length === 0 ? (
        <EmptyState
          title="Sin resultados"
          message={
            searchQuery
              ? `No se encontraron oportunidades para "${searchQuery}"`
              : "No hay oportunidades en esta categoría."
          }
          action={{
            label: "Crear desde búsqueda",
            onClick: () => {
              router.push("/search");
            },
          }}
        />
      ) : (
        <>
          <div className="space-y-3">
            {paginated.map((opp: any) => (
              <OpportunityCard
                key={opp.id}
                id={opp.id}
                opportunity={opp}
              />
            ))}
          </div>
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
          />
        </>
      )}
    </div>
  );
}
