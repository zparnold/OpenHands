import React from "react";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import OrganizationService from "#/api/organization-service/organization-service.api";
import type { OrganizationMember } from "#/api/organization-service/organization-service.types";
import { BrandButton } from "#/components/features/settings/brand-button";
import { I18nKey } from "#/i18n/declaration";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";

interface MemberListProps {
  orgId: string;
  members: OrganizationMember[];
  currentUserId: string | null;
  isAdmin: boolean;
}

export function MemberList({
  orgId,
  members,
  currentUserId,
  isAdmin,
}: MemberListProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const updateRoleMutation = useMutation({
    mutationFn: ({
      userId,
      role,
    }: {
      userId: string;
      role: "admin" | "member";
    }) => OrganizationService.updateMemberRole(orgId, userId, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["organizations", orgId, "members"],
      });
      displaySuccessToast(t(I18nKey.ORG$ROLE_UPDATED));
    },
    onError: (error) => {
      const msg = retrieveAxiosErrorMessage(error);
      displayErrorToast(msg || t(I18nKey.ORG$ROLE_UPDATE_FAILED));
    },
  });

  const removeMemberMutation = useMutation({
    mutationFn: (userId: string) =>
      OrganizationService.removeMember(orgId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["organizations", orgId, "members"],
      });
      displaySuccessToast(t(I18nKey.ORG$MEMBER_REMOVED));
    },
    onError: (error) => {
      const msg = retrieveAxiosErrorMessage(error);
      displayErrorToast(msg || t(I18nKey.ORG$REMOVE_MEMBER_FAILED));
    },
  });

  return (
    <div className="flex flex-col gap-3">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-neutral-400 border-b border-neutral-700">
            <th className="pb-2 font-medium">{t(I18nKey.ORG$USER)}</th>
            <th className="pb-2 font-medium">{t(I18nKey.ORG$ROLE)}</th>
            {isAdmin && (
              <th className="pb-2 font-medium">{t(I18nKey.ORG$ACTIONS)}</th>
            )}
          </tr>
        </thead>
        <tbody>
          {members.map((member) => {
            const isSelf = member.user_id === currentUserId;
            return (
              <tr
                key={member.user_id}
                className="border-b border-neutral-800 hover:bg-neutral-800/50"
              >
                <td className="py-3">
                  <div className="flex flex-col">
                    <span className="font-medium">
                      {member.display_name || member.email || member.user_id}
                    </span>
                    {member.email && member.display_name && (
                      <span className="text-xs text-neutral-400">
                        {member.email}
                      </span>
                    )}
                  </div>
                </td>
                <td className="py-3">
                  {isAdmin && !isSelf ? (
                    <select
                      value={member.role}
                      onChange={(e) =>
                        updateRoleMutation.mutate({
                          userId: member.user_id,
                          role: e.target.value as "admin" | "member",
                        })
                      }
                      className="bg-neutral-800 border border-neutral-600 rounded px-2 py-1 text-sm"
                      disabled={updateRoleMutation.isPending}
                    >
                      <option value="admin">{t(I18nKey.ORG$ROLE_ADMIN)}</option>
                      <option value="member">
                        {t(I18nKey.ORG$ROLE_MEMBER)}
                      </option>
                    </select>
                  ) : (
                    <span
                      className={`inline-block px-2 py-0.5 text-xs rounded ${
                        member.role === "admin"
                          ? "bg-blue-900/40 text-blue-300"
                          : "bg-neutral-700 text-neutral-300"
                      }`}
                    >
                      {member.role === "admin"
                        ? t(I18nKey.ORG$ROLE_ADMIN)
                        : t(I18nKey.ORG$ROLE_MEMBER)}
                    </span>
                  )}
                </td>
                {isAdmin && (
                  <td className="py-3">
                    {!isSelf && (
                      <BrandButton
                        variant="ghost-danger"
                        type="button"
                        isDisabled={removeMemberMutation.isPending}
                        onClick={() =>
                          removeMemberMutation.mutate(member.user_id)
                        }
                      >
                        {t(I18nKey.ORG$REMOVE)}
                      </BrandButton>
                    )}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
