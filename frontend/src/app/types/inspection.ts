/** TypeScript interfaces for the Inspection Session module. */

export type InspectionItemStatus = 'GOOD' | 'WARNING' | 'BAD' | 'UNKNOWN';
export type InspectionSessionStatus = 'DRAFT' | 'COMPLETED';
export type SeverityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface InspectionSession {
  id: string;
  vehicle_id: string;
  status: InspectionSessionStatus;
  current_category_order: number;
  total_repair_cost: number;
  total_defects: number;
  total_critical_defects: number;
  risk_level: string | null;
  recommendation: string | null;
  overall_condition: number | null;
  notes: string | null;
  summary: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
  completed_at: string | null;
}

export interface InspectionObservation {
  id: string;
  session_id: string;
  category_id: string;
  item_id: string;
  status: InspectionItemStatus;
  notes: string | null;
  estimated_repair_cost: number | null;
  severity: SeverityLevel;
  created_at: string | null;
  updated_at: string | null;
}

export interface InspectionPhoto {
  id: string;
  observation_id: string;
  session_id: string;
  file_path: string;
  file_name: string | null;
  mime_type: string | null;
  file_size_bytes: number | null;
  ai_analysis_status: string;
  created_at: string | null;
}

export interface CatalogItem {
  id: string;
  label: string;
  description: string;
  order: number;
  is_safety_relevant: boolean;
  has_cost_estimate: boolean;
  allows_photos: boolean;
  status: InspectionItemStatus;
  notes: string | null;
  estimated_repair_cost: number | null;
  severity: SeverityLevel;
  observation_id: string | null;
}

export interface CatalogCategory {
  id: string;
  label: string;
  icon: string;
  description: string;
  order: number;
  items: CatalogItem[];
}

export interface InspectionSessionDetail {
  session: InspectionSession;
  observations: InspectionObservation[];
  photos: InspectionPhoto[];
  catalog: CatalogCategory[];
}

export interface InspectionSummary {
  session_id: string;
  vehicle_id: string;
  status: InspectionSessionStatus;
  progress: {
    reviewed_items: number;
    total_items: number;
    percentage: number;
  };
  defects: {
    total: number;
    good: number;
    warning: number;
    bad: number;
    critical: number;
  };
  costs: {
    total_repair_cost: number;
    parts_cost: number;
    labor_cost: number;
    paint_and_body_cost: number;
  };
  overall_condition: number | null;
  risk_level: string;
  recommendation: string;
  defect_items: Array<{
    category: string;
    description: string;
    severity: number;
    estimated_repair_cost: number;
    is_safety_relevant: boolean;
  }>;
  repair_estimate: {
    total_repair_cost: number;
    parts_cost: number;
    labor_cost: number;
  };
  inspection_result: {
    overall_condition: number;
    has_accident_history: boolean;
  };
}

export interface CreateSessionRequest {
  vehicle_id: string;
}

export interface UpdateObservationRequest {
  category_id: string;
  item_id: string;
  status: InspectionItemStatus;
  notes?: string | null;
  estimated_repair_cost?: number | null;
}

export interface UploadPhotoRequest {
  observation_id: string;
  file_path: string;
  file_name?: string | null;
  mime_type?: string | null;
  file_size_bytes?: number | null;
}
