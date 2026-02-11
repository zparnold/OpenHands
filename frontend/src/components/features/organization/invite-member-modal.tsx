import React, { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import OrganizationService from "#/api/organization-service/organization-service.api";
import { BrandButton } from "#/components/features/settings/brand-button";
import { I18nKey } from "#/i18n/declaration";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";

interface InviteMemberModalProps {
  orgId: string;
  onClose: () => void;
}

export function InviteMemberModal({ orgId, onClose }: InviteMemberModalProps) {
  const { t } = useTranslation();
  const [userId, setUserId] = useState("");
  const [role, setRole] = useState<"admin" | "member">("member");
  const queryClient = useQueryClient();

  const addMemberMutation = useMutation({
    mutationFn: () =>
      OrganizationService.addMember(orgId, { user_id: userId, role }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["organizations", orgId, "members"],
      });
      displaySuccessToast(t(I18nKey.ORG$MEMBER_ADDED));
      onClose();
    },
    onError: (error) => {
      const msg = retrieveAxiosErrorMessage(error);
      displayErrorToast(msg || t(I18nKey.ORG$ADD_MEMBER_FAILED));
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-neutral-900 border border-neutral-700 rounded-lg p-6 w-full max-w-md">
        <h3 className="text-lg font-semibold mb-4">
          {t(I18nKey.ORG$ADD_MEMBER)}
        </h3>

        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <label htmlFor="user-id-input" className="text-sm text-neutral-400">
              {t(I18nKey.ORG$USER_ID)}
            </label>
            <input
              id="user-id-input"
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder={t(I18nKey.ORG$ENTER_USER_ID)}
              className="bg-neutral-800 border border-neutral-600 rounded px-3 py-2 text-sm"
            />
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="role-select" className="text-sm text-neutral-400">
              {t(I18nKey.ORG$ROLE)}
            </label>
            <select
              id="role-select"
              value={role}
              onChange={(e) => setRole(e.target.value as "admin" | "member")}
              className="bg-neutral-800 border border-neutral-600 rounded px-3 py-2 text-sm"
            >
              <option value="member">{t(I18nKey.ORG$ROLE_MEMBER)}</option>
              <option value="admin">{t(I18nKey.ORG$ROLE_ADMIN)}</option>
            </select>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <BrandButton variant="secondary" type="button" onClick={onClose}>
            {t(I18nKey.COMMON$CANCEL)}
          </BrandButton>
          <BrandButton
            variant="primary"
            type="button"
            isDisabled={!userId.trim() || addMemberMutation.isPending}
            onClick={() => addMemberMutation.mutate()}
          >
            {addMemberMutation.isPending
              ? t(I18nKey.ORG$ADDING)
              : t(I18nKey.ORG$ADD_MEMBER)}
          </BrandButton>
        </div>
      </div>
    </div>
  );
}
