"use client";

import { FileText, Download } from "lucide-react";
import { GeneratedFile } from "@/app/hooks/useOpportunityDetail";

interface GeneratedFilesProps {
  files: GeneratedFile[];
}

export function GeneratedFiles({ files }: GeneratedFilesProps) {
  if (!files || files.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-white">Archivos generados</h3>
      <div className="space-y-2">
        {files.map((file) => (
          <div
            key={file.id}
            className="flex items-center justify-between p-3 rounded-xl bg-[#16161f] border border-[#1e1e2d] hover:border-[#2a2a3d] transition-colors"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-primary-600/10 border border-primary-600/20 flex items-center justify-center text-primary-400 shrink-0">
                <FileText className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-white truncate">{file.name}</p>
                <p className="text-[10px] text-secondary-500">{file.size} · {file.created_at}</p>
              </div>
            </div>

            <a
              href={file.url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 rounded-lg bg-[#111118] text-secondary-400 hover:text-white hover:bg-[#1e1e2d] transition-colors shrink-0"
            >
              <Download className="w-4 h-4" />
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}
