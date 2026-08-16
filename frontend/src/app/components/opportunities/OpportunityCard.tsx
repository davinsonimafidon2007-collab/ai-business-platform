"use client";

import Image from "next/image";
import Link from "next/link";

interface OpportunityCardProps {
  id: string;
  image: string;
  title: string;
  year: number;
  price: number;
  marketPrice: number;
  margin: number;
  status: string;
  phase: string;
  agent: string;
}

export function OpportunityCard({
  id,
  image,
  title,
  year,
  price,
  marketPrice,
  margin,
  status,
  phase,
  agent,
}: OpportunityCardProps) {
  return (
    <Link
      href={`/opportunities/${id}`}
      className="flex flex-col sm:flex-row gap-4 p-4 rounded-2xl bg-[#111118] border border-[#1e1e2d] hover:border-[#2a2a3d] transition-all"
    >
      <div className="relative w-full sm:w-32 h-32 sm:h-24 rounded-xl overflow-hidden shrink-0 bg-[#16161f]">
        <Image
          src={image}
          alt={title}
          fill
          className="object-cover"
          sizes="(max-width: 640px) 100vw, 128px"
        />
      </div>

      <div className="flex-1 flex flex-col justify-between">
        <div>
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-semibold text-white text-base leading-snug">{title}</h3>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 capitalize">
              {status}
            </span>
          </div>

          <p className="text-xs text-secondary-400 mt-1">
            Año {year} · Agente: {agent}
          </p>
        </div>

        <div className="flex items-center justify-between gap-2 mt-3 pt-3 border-t border-[#1e1e2d]">
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-base font-bold text-white">
                {price.toLocaleString("es-ES")} €
              </span>
              <span className="text-xs text-secondary-500 line-through">
                {marketPrice.toLocaleString("es-ES")} €
              </span>
            </div>
            <p className="text-[11px] text-emerald-400 font-medium">
              +{margin}% margen est.
            </p>
          </div>

          <div className="text-right">
            <span className="text-[11px] text-secondary-400 font-medium">{phase}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
