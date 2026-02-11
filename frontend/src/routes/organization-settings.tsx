import React, { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import OrganizationService from "#/api/organization-service/organization-service.api";
import {
  useOrganizations,
  useOrganizationMembers,
} from "#/hooks/query/use-organizations";
import { useCurrentUser } from "#/hooks/query/use-current-user";
import { MemberList } from "#/components/features/organization/member-list";
import { InviteMemberModal } from "#/components/features/organization/invite-member-modal";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { I18nKey } from "#/i18n/declaration";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { retrieveAxiosErrorMessage } from "#/utils/retrieve-axios-error-message";

function OrganizationSettingsScreen() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data: currentUser } = useCurrentUser();
  const { data: organizations, isLoading: orgsLoading } = useOrganizations();
  const selectedOrg = organizations?.[0];
  const orgId = selectedOrg?.id;

  const { data: members, isLoading: membersLoading } =
    useOrganizationMembers(orgId);

  const [orgName, setOrgName] = useState("");
  const [nameHasChanged, setNameHasChanged] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);

  // Sync org name from server data
  React.useEffect(() => {
    if (selectedOrg?.name && !nameHasChanged) {
      setOrgName(selectedOrg.name);
    }
  }, [selectedOrg?.name]);

  const currentUserId = currentUser?.id ?? null;
  const currentUserMembership = members?.find(
    (m) => m.user_id === currentUserId,
  );
  const isAdmin = currentUserMembership?.role === "admin";

  const updateOrgMutation = useMutation({
    mutationFn: () =>
      OrganizationService.updateOrganization(orgId!, { name: orgName }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["organizations"] });
      setNameHasChanged(false);
      displaySuccessToast(t(I18nKey.ORG$UPDATED));
    },
    onError: (error) => {
      const msg = retrieveAxiosErrorMessage(error);
      displayErrorToast(msg || t(I18nKey.ORG$UPDATE_FAILED));
    },
  });

  if (orgsLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <span className="text-neutral-400">{t(I18nKey.COMMON$LOADING)}</span>
      </div>
    );
  }

  if (!selectedOrg) {
    return (
      <div className="flex items-center justify-center py-12">
        <span className="text-neutral-400">{t(I18nKey.ORG$NO_ORG_FOUND)}</span>
      </div>
    );
  }

  const membersContent = (() => {
    if (membersLoading) {
      return (
        <span className="text-neutral-400 text-sm">
          {t(I18nKey.ORG$LOADING_MEMBERS)}
        </span>
      );
    }
    if (members && members.length > 0) {
      return (
        <MemberList
          orgId={orgId!}
          members={members}
          currentUserId={currentUserId}
          isAdmin={isAdmin}
        />
      );
    }
    return (
      <span className="text-neutral-400 text-sm">
        {t(I18nKey.ORG$NO_MEMBERS)}
      </span>
    );
  })();

  return (
    <div className="flex flex-col gap-8">
      {/* Organization name */}
      <section className="flex flex-col gap-4">
        <h3 className="text-base font-semibold">{t(I18nKey.ORG$DETAILS)}</h3>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (nameHasChanged && isAdmin) {
              updateOrgMutation.mutate();
            }
          }}
          className="flex flex-col gap-4"
        >
          <SettingsInput
            testId="org-name-input"
            label={t(I18nKey.ORG$NAME)}
            type="text"
            value={orgName}
            onChange={(value) => {
              setOrgName(value);
              setNameHasChanged(value !== selectedOrg.name);
            }}
            isDisabled={!isAdmin}
          />
          {isAdmin && nameHasChanged && (
            <BrandButton
              variant="primary"
              type="submit"
              isDisabled={updateOrgMutation.isPending || !orgName.trim()}
            >
              {updateOrgMutation.isPending
                ? t(I18nKey.COMMON$SAVING)
                : t(I18nKey.COMMON$SAVE)}
            </BrandButton>
          )}
        </form>
      </section>

      {/* Members section */}
      <section className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">{t(I18nKey.ORG$MEMBERS)}</h3>
          {isAdmin && (
            <BrandButton
              variant="secondary"
              type="button"
              onClick={() => setShowInviteModal(true)}
            >
              {t(I18nKey.ORG$ADD_MEMBER)}
            </BrandButton>
          )}
        </div>

        {membersContent}
      </section>

      {/* Invite modal */}
      {showInviteModal && orgId && (
        <InviteMemberModal
          orgId={orgId}
          onClose={() => setShowInviteModal(false)}
        />
      )}
    </div>
  );
}

export default OrganizationSettingsScreen;
