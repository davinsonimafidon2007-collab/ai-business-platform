// =============================================================================
// Vehicle Score
// =============================================================================
export interface VehicleScore {
  score: number;
  category: string;
  strengths: string[];
  weaknesses: string[];
}

// =============================================================================
// Market Estimation
// =============================================================================
export interface MarketEstimation {
  market_price: number;
  confidence: number;
  supply_level: number;
  demand_level: number;
  market_trend: string;
  comparable_count: number;
  notes: string[];
}

// =============================================================================
// Cost Breakdown
// =============================================================================
export interface CostBreakdown {
  purchase_price: number;
  transport_cost: number;
  registration_cost: number;
  taxes: number;
  inspection_cost: number;
  repair_estimate: number;
  commission_cost: number;
  miscellaneous_cost: number;
  total_fixed_costs: number;
  total_variable_costs: number;
  total_cost: number;
}

// =============================================================================
// Profit Analysis
// =============================================================================
export interface ProfitAnalysis {
  purchase_price: number;
  transport_cost: number;
  registration_cost: number;
  taxes: number;
  inspection_cost: number;
  repair_estimate: number;
  commission_cost: number;
  miscellaneous_cost: number;
  total_cost: number;
  estimated_sale_price: number;
  gross_profit: number;
  net_profit: number;
  roi_percentage: number;
  profit_margin_percentage: number;
  risk_level: string;
  recommendation: string;
  cost_breakdown: CostBreakdown;
}

// =============================================================================
// Opportunity Analysis
// =============================================================================
export interface OpportunityAnalysis {
  overall_score: number;
  opportunity_level: string;
  recommendation: string;
  estimated_profit: number;
  roi: number;
  market_confidence: number;
  risk_level: string;
  strengths: string[];
  weaknesses: string[];
}

// =============================================================================
// Search Result Item
// =============================================================================
export interface SearchResultItem {
  source: string | null;
  external_id: string | null;
  url: string | null;
  brand: string | null;
  model: string | null;
  year: number | null;
  mileage: number | null;
  fuel_type: string | null;
  transmission: string | null;
  power_hp: number | null;
  price: number | null;
  currency: string | null;
  location: string | null;
  images: string[];
  description: string | null;
  vehicle_score: VehicleScore | null;
  market_estimation: MarketEstimation | null;
  profit_analysis: ProfitAnalysis | null;
  opportunity: OpportunityAnalysis | null;
}

// =============================================================================
// Search Summary
// =============================================================================
export interface SearchSummary {
  total_results: number;
  excellent: number;
  good: number;
  average: number;
  poor: number;
  rejected: number;
}

// =============================================================================
// Search API Response
// =============================================================================
export interface SearchAPIResponse {
  summary: SearchSummary;
  results: SearchResultItem[];
}

// =============================================================================
// Search API Request
// =============================================================================
export interface SearchAPIRequest {
  query: string;
  providers?: string[];
  max_results?: number;
  min_price?: number | null;
  max_price?: number | null;
}

// =============================================================================
// Search Filters (frontend-only extended version)
// =============================================================================
export interface SearchFilters {
  query: string;
  brand?: string;
  model?: string;
  min_price?: number;
  max_price?: number;
  min_mileage?: number;
  max_mileage?: number;
  fuel_type?: string;
  transmission?: string;
  min_year?: number;
  max_year?: number;
  provider?: string;
  sort_by?: string;
  sort_order?: "asc" | "desc";
}

// =============================================================================
// Search History
// =============================================================================
export interface SearchHistory {
  id: string;
  query: string;
  results_count: number;
  execution_time: number;
  created_at: string;
  filters?: Record<string, unknown>;
}

// =============================================================================
// Dashboard Stats
// =============================================================================
export interface DashboardStats {
  total_searches: number;
  total_vehicles: number;
  excellent_opportunities: number;
  average_roi: number;
  average_profit: number;
  recommendation_distribution: Record<string, number>;
}