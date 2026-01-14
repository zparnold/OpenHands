import OpenHands from "#/api/open-hands-axios";
import {
  InviteRequest,
  InviteRequestCreate,
  InviteRequestCount,
  InviteRequestResponse,
  InviteRequestStatusUpdate,
} from "./invite.types";

export class InviteService {
  /**
   * Create a new invite request (public endpoint)
   */
  static async createInviteRequest(
    data: InviteRequestCreate,
  ): Promise<InviteRequestResponse> {
    const response = await OpenHands.post<InviteRequestResponse>(
      "/api/invite/request",
      data,
    );
    return response.data;
  }

  /**
   * Get all invite requests (admin only)
   */
  static async getInviteRequests(
    statusFilter?: string,
    limit: number = 100,
    offset: number = 0,
  ): Promise<InviteRequest[]> {
    const params = new URLSearchParams();
    if (statusFilter) params.append("status_filter", statusFilter);
    params.append("limit", limit.toString());
    params.append("offset", offset.toString());

    const response = await OpenHands.get<InviteRequest[]>(
      `/api/invite/requests?${params.toString()}`,
    );
    return response.data;
  }

  /**
   * Update the status of an invite request (admin only)
   */
  static async updateInviteStatus(
    email: string,
    data: InviteRequestStatusUpdate,
  ): Promise<InviteRequestResponse> {
    const response = await OpenHands.patch<InviteRequestResponse>(
      `/api/invite/requests/${encodeURIComponent(email)}`,
      data,
    );
    return response.data;
  }

  /**
   * Get the count of invite requests (admin only)
   */
  static async getInviteRequestsCount(
    statusFilter?: string,
  ): Promise<InviteRequestCount> {
    const params = new URLSearchParams();
    if (statusFilter) params.append("status_filter", statusFilter);

    const response = await OpenHands.get<InviteRequestCount>(
      `/api/invite/requests/count?${params.toString()}`,
    );
    return response.data;
  }
}
