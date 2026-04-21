export type Role = "admin" | "worker" | "risk_manager" | "expert";
export type RiskStatus = "pending" | "draft" | "assessed";
export type RiskLevel = "low" | "medium" | "high" | "critical";
export type ThemeMode = "day" | "night";

export interface ExpertUser {
  id?: number;
  full_name: string;
  email: string;
  role: Role;
  joined_at: string;
  is_approved?: boolean;
}

export interface ApiAssessment {
  id?: number;
  risk_id: string | number;
  probability: number;
  impact_score: number;
  recommendation: string;
  severity_level?: string;
  date: string;
  expert_id?: number;
}

export interface Risk {
  id: string;
  title: string;
  description: string;
  category: string;
  owner: string;
  expert?: string | null;
  priority: number;
  assigned_date: string;
  status: RiskStatus;
  impact_level?: string;
  incident_count?: number;
  measure_count?: number;
  assessment_count?: number;
  incidents?: string[];
  mitigations?: string[];
  my_assessment?: ApiAssessment | null;
}

export interface SubmittedAssessment {
  id: number;
  risk_id: string;
  risk_title: string;
  probability: number;
  impact_score: number;
  recommendation: string;
  severity_level: string;
  date: string;
}

export interface DraftAssessment {
  probability: number;
  impact_score: number;
  recommendation: string;
  date: string;
}
