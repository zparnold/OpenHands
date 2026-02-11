export interface Organization {
  id: string;
  name: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface OrganizationMember {
  user_id: string;
  email: string | null;
  display_name: string | null;
  role: "admin" | "member";
  joined_at: string | null;
}

export interface UpdateOrganizationRequest {
  name: string;
}

export interface AddMemberRequest {
  user_id: string;
  role: "admin" | "member";
}

export interface UpdateMemberRoleRequest {
  role: "admin" | "member";
}
