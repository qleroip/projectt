export type UserRole = "admin" | "risk_manager" | "expert" | "worker";

export type CurrentUser = {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  joined_at: string;
  is_approved: boolean;
};

export type IncidentPayload = {
  title: string;
  description: string;
  category: string;
  impact_level: string;
  occurrence_date: string;
  actual_loss: number;
};

export type IncidentResponse = {
  id: string;
  status: string;
};

export type IncidentHistoryItem = IncidentResponse & {
  title: string;
  sentAt: string;
};
