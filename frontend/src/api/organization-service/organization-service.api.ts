import { openHands } from "../open-hands-axios";
import type {
  Organization,
  OrganizationMember,
  UpdateOrganizationRequest,
  AddMemberRequest,
  UpdateMemberRoleRequest,
} from "./organization-service.types";

class OrganizationService {
  /** List organizations the current user belongs to. */
  static async listOrganizations(): Promise<Organization[]> {
    const { data } = await openHands.get<Organization[]>(
      "/api/v1/organizations",
    );
    return data;
  }

  /** Get a single organization by ID. */
  static async getOrganization(orgId: string): Promise<Organization> {
    const { data } = await openHands.get<Organization>(
      `/api/v1/organizations/${orgId}`,
    );
    return data;
  }

  /** Update an organization's name. */
  static async updateOrganization(
    orgId: string,
    body: UpdateOrganizationRequest,
  ): Promise<Organization> {
    const { data } = await openHands.put<Organization>(
      `/api/v1/organizations/${orgId}`,
      body,
    );
    return data;
  }

  /** List members of an organization. */
  static async listMembers(orgId: string): Promise<OrganizationMember[]> {
    const { data } = await openHands.get<OrganizationMember[]>(
      `/api/v1/organizations/${orgId}/members`,
    );
    return data;
  }

  /** Add a member to an organization. */
  static async addMember(
    orgId: string,
    body: AddMemberRequest,
  ): Promise<OrganizationMember> {
    const { data } = await openHands.post<OrganizationMember>(
      `/api/v1/organizations/${orgId}/members`,
      body,
    );
    return data;
  }

  /** Update a member's role. */
  static async updateMemberRole(
    orgId: string,
    userId: string,
    body: UpdateMemberRoleRequest,
  ): Promise<OrganizationMember> {
    const { data } = await openHands.put<OrganizationMember>(
      `/api/v1/organizations/${orgId}/members/${userId}`,
      body,
    );
    return data;
  }

  /** Remove a member from an organization. */
  static async removeMember(orgId: string, userId: string): Promise<void> {
    await openHands.delete(`/api/v1/organizations/${orgId}/members/${userId}`);
  }
}

export default OrganizationService;
