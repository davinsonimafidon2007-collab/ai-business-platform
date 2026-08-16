"use client";

import Image from "next/image";
import { ArrowRight } from "lucide-react";

interface ApprovalReviewCardProps {
  image: string;
  title: string;
  category: string;
  description: string;
  detail?: string;
  time: string;
  onReview: () => void;
}

export function ApprovalReviewCard({
  image,
  title,
  category,
  description,
  detail,
  time,
  onReview,
}: ApprovalReviewCardProps) {
  return (
    <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-[#111118] border border-[#1e1e2d] hover:border-[#2a2a3d] transition-all">
      <div className="relative w-16 h-16 rounded-xl overflow-hidden shrink-0 bg-[#16161f]">
        <Image
          src={image}
          alt={title}
          fill
          className="object-cover"
          sizes="64px"
        />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 rounded-md text-[10px] font-semibold bg-primary-600/10 text-primary-400 border border-primary-600/20">
            {category}
          </span>
          <span className="text-[11px] text-secondary-500">{time}</span>
        </div>
        <h3 className="font-semibold text-white text-sm truncate mt-1">{title}</h3>
        <p className="text-xs text-secondary-400 truncate">{description}</p>
        {detail && <p className="text-[11px] text-secondary-500 truncate">{detail}</p>}
      </div>

      <button
        onClick={onReview}
        className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-primary-600 hover:bg-primary-500 text-white text-xs font-semibold shrink-0 transition-colors"
      >
        <span>Revisar</span>
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
