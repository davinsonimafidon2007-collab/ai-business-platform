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
// Negotiation
// =============================================================================
export interface NegotiationArgument {
  argument: string;
  economic_impact: number;
  category: string;
  severity: number;
}

export interface NegotiationScript {
  opening: string;
  defect_based_points: string[];
  market_based_points: string[];
  closing: string;
}

export interface NegotiationResult {
  estimated_vehicle_value: number;
  recommended_initial_offer: number;
  recommended_counter_offer: number;
  maximum_purchase_price: number;
  walk_away_price: number;
  expected_profit: number;
  expected_roi: number;
  negotiation_arguments: NegotiationArgument[];
  negotiation_script: NegotiationScript;
  recommendation: "BUY" | "NEGOTIATE" | "WALK_AWAY";
  leverage_score: number;
  price_gap: number;
  discount_needed: number;
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
  negotiation: NegotiationResult | null;
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
  brand?: string;
  model?: string;
  min_year?: number;
  max_year?: number;
  min_mileage?: number;
  max_mileage?: number;
  fuel_type?: string;
  transmission?: string;
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
  timestamp: string;
  providers_used?: string | null;
  results_count?: number | null;
  execution_time?: number | null;
}

// =============================================================================
// Dashboard Stats
// =============================================================================
export interface DashboardStats {
  total_searches: number;
  recent_searches: number;
  average_results_per_search: number;
  average_execution_time: number;
  provider_stats: Record<string, number>;
}
