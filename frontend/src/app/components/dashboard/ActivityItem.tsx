"use client";

import { CheckCircle2, FileText, Search, User, Car, AlertTriangle, Bot, Workflow } from "lucide-react";

export interface ActivityItemProps {
  icon: "completed" | "file" | "search" | "user" | "car" | "alert" | "agent" | "workflow";
  text: string;
  time: string;
}

const iconMap = {
  completed: CheckCircle2,
  file: FileText,
  search: Search,
  user: User,
  car: Car,
  alert: AlertTriangle,
  agent: Bot,
  workflow: Workflow,
};

const iconColorMap = {
  completed: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  file: "text-primary-400 bg-primary-600/10 border-primary-600/20",
  search: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  user: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  car: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  alert: "text-rose-400 bg-rose-500/10 border-rose-500/20",
  agent: "text-indigo-400 bg-indigo-500/10 border-indigo-500/20",
  workflow: "text-cyan-400 bg-cyan-500/10 border-cyan-500/20",
};

export function ActivityItem({ icon, text, time }: ActivityItemProps) {
  const Icon = iconMap[icon] || CheckCircle2;
  const colorClass = iconColorMap[icon] || iconColorMap.completed;

  return (
    <div className="flex items-center gap-3 py-3">
      <div className={`w-8 h-8 rounded-xl border flex items-center justify-center shrink-0 ${colorClass}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-white truncate">{text}</p>
        <p className="text-[10px] text-secondary-500 mt-0.5">{time}</p>
      </div>
    </div>
  );
}
