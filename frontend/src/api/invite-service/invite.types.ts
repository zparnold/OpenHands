export interface InviteRequest {
  id: number;
  email: string;
  status: "pending" | "approved" | "rejected";
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface InviteRequestCreate {
  email: string;
  notes?: string;
}

export interface InviteRequestStatusUpdate {
  status: "pending" | "approved" | "rejected";
  notes?: string;
}

export interface InviteRequestResponse {
  message: string;
  email?: string;
  status?: string;
}

export interface InviteRequestCount {
  count: number;
  status: string | null;
}
