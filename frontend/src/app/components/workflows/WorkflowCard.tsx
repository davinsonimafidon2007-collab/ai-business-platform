"use client";

import { Workflow, Play, Pause, AlertTriangle, CheckCircle } from "lucide-react";

interface WorkflowCardProps {
  id: string;
  name: string;
  description: string;
  status: "running" | "paused" | "failed" | "completed";
  phases: number;
  completedPhases: number;
  lastRun: string;
}

const STATUS_CONFIG = {
  running: { label: "En ejecución", icon: Play, color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" },
  paused: { label: "Pausado", icon: Pause, color: "bg-amber-500/10 text-amber-400 border-amber-500/20" },
  failed: { label: "Fallido", icon: AlertTriangle, color: "bg-rose-500/10 text-rose-400 border-rose-500/20" },
  completed: { label: "Completado", icon: CheckCircle, color: "bg-blue-500/10 text-blue-400 border-blue-500/20" },
};

export function WorkflowCard({
  name,
  description,
  status,
  phases,
  completedPhases,
  lastRun,
}: WorkflowCardProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.paused;
  const Icon = config.icon;
  const progress = Math.round((completedPhases / phases) * 100) || 0;

  return (
    <div className="p-4 rounded-2xl bg-[#111118] border border-[#1e1e2d] hover:border-[#2a2a3d] transition-all space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary-600/10 border border-primary-600/20 flex items-center justify-center text-primary-400">
            <Workflow className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-semibold text-white text-base">{name}</h3>
            <p className="text-xs text-secondary-500">Última ejec.: {lastRun}</p>
          </div>
        </div>

        <span className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${config.color}`}>
          <Icon className="w-3.5 h-3.5" />
          {config.label}
        </span>
      </div>

      <p className="text-xs text-secondary-300 line-clamp-2">{description}</p>

      <div className="space-y-1.5 pt-2 border-t border-[#1e1e2d]">
        <div className="flex items-center justify-between text-xs text-secondary-400">
          <span>Progreso</span>
          <span className="font-medium text-white">{completedPhases} / {phases} fases ({progress}%)</span>
        </div>
        <div className="w-full h-1.5 rounded-full bg-[#16161f] overflow-hidden">
          <div
            className="h-full bg-primary-600 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}
