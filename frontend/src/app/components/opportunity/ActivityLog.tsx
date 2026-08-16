"use client";

import { ActivityItem as ActivityItemComponent } from "@/app/components/dashboard/ActivityItem";
import { ActivityItem as ActivityItemType } from "@/app/hooks/useOpportunityDetail";

interface ActivityLogProps {
  items: ActivityItemType[];
}

export function ActivityLog({ items }: ActivityLogProps) {
  if (!items || items.length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-secondary-500">Sin actividad registrada</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-[#1e1e2d]">
      {items.map((item) => (
        <ActivityItemComponent
          key={item.id}
          icon={item.type}
          text={`${item.title} — ${item.description}`}
          time={item.created_at}
        />
      ))}
    </div>
  );
}
