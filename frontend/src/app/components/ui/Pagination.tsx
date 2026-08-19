"use client";

import { cn } from "@/app/utils/cn";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface PaginationProps {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  if (totalPages <= 1) return null;

  const pages = Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
    if (totalPages <= 5) return i + 1;
    if (currentPage <= 3) return i + 1;
    if (currentPage >= totalPages - 2) return totalPages - 4 + i;
    return currentPage - 2 + i;
  });

  return (
    <nav className="flex items-center justify-center gap-1.5 mt-6" aria-label="Navegación de páginas">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        aria-label="Página anterior"
        className="w-9 h-9 rounded-lg flex items-center justify-center text-secondary-400 hover:text-white hover:bg-[#1a1a24] disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
      >
        <ChevronLeft className="w-4 h-4" aria-hidden="true" />
      </button>

      {pages.map((page) => (
        <button
          key={page}
          onClick={() => onPageChange(page)}
          aria-label={`Página ${page}`}
          aria-current={currentPage === page ? "page" : undefined}
          className={cn(
            "w-9 h-9 rounded-lg text-xs font-semibold transition-colors cursor-pointer",
            currentPage === page
              ? "bg-primary-600 text-white"
              : "text-secondary-400 hover:text-white hover:bg-[#1a1a24]"
          )}
        >
          {page}
        </button>
      ))}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        aria-label="Página siguiente"
        className="w-9 h-9 rounded-lg flex items-center justify-center text-secondary-400 hover:text-white hover:bg-[#1a1a24] disabled:opacity-30 disabled:hover:bg-transparent transition-colors cursor-pointer"
      >
        <ChevronRight className="w-4 h-4" aria-hidden="true" />
      </button>
    </nav>
  );
}
