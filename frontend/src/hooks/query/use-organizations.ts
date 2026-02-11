import { useQuery } from "@tanstack/react-query";
import OrganizationService from "#/api/organization-service/organization-service.api";

export const useOrganizations = () =>
  useQuery({
    queryKey: ["organizations"],
    queryFn: OrganizationService.listOrganizations,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 15,
  });

export const useOrganization = (orgId: string | undefined) =>
  useQuery({
    queryKey: ["organizations", orgId],
    queryFn: () => OrganizationService.getOrganization(orgId!),
    enabled: !!orgId,
    staleTime: 1000 * 60 * 5,
    gcTime: 1000 * 60 * 15,
  });

export const useOrganizationMembers = (orgId: string | undefined) =>
  useQuery({
    queryKey: ["organizations", orgId, "members"],
    queryFn: () => OrganizationService.listMembers(orgId!),
    enabled: !!orgId,
    staleTime: 1000 * 60 * 2,
    gcTime: 1000 * 60 * 10,
  });
