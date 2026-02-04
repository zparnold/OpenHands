import { useTranslation } from "react-i18next";
import { I18nKey } from "#/i18n/declaration";
import { SettingsInput } from "../settings-input";
import { AzureDevOpsTokenHelpAnchor } from "./azure-devops-token-help-anchor";
import { KeyStatusIcon } from "../key-status-icon";
import { Typography } from "#/ui/typography";

interface AzureDevOpsTokenInputProps {
  onChange: (value: string) => void;
  onAzureDevOpsHostChange: (value: string) => void;
  isAzureDevOpsTokenSet: boolean;
  name: string;
  azureDevOpsHostSet: string | null | undefined;
}

/** Extract organization name for display (e.g. "dev.azure.com/myorg" -> "myorg") */
function getDisplayOrg(host: string): string {
  const trimmed = host.trim();
  if (!trimmed) return trimmed;
  const parts = trimmed.split("/").filter(Boolean);
  return parts.length > 1 ? parts[parts.length - 1] : trimmed;
}

export function AzureDevOpsTokenInput({
  onChange,
  onAzureDevOpsHostChange,
  isAzureDevOpsTokenSet,
  name,
  azureDevOpsHostSet,
}: AzureDevOpsTokenInputProps) {
  const { t } = useTranslation();
  const hasSavedOrg = azureDevOpsHostSet && azureDevOpsHostSet.trim() !== "";
  const displayOrg = hasSavedOrg ? getDisplayOrg(azureDevOpsHostSet!) : "";

  return (
    <div className="flex flex-col gap-6">
      {hasSavedOrg && (
        <Typography.Text
          className="text-sm text-gray-400"
          testId="azure-devops-connected-org"
        >
          {t(I18nKey.GIT$AZURE_DEVOPS_CONNECTED_TO, { org: displayOrg })}
        </Typography.Text>
      )}

      <SettingsInput
        testId={name}
        name={name}
        onChange={onChange}
        label={t(I18nKey.GIT$AZURE_DEVOPS_TOKEN)}
        type="password"
        className="w-full max-w-[680px]"
        placeholder={isAzureDevOpsTokenSet ? "<hidden>" : ""}
        startContent={
          isAzureDevOpsTokenSet && (
            <KeyStatusIcon
              testId="azure-devops-set-token-indicator"
              isSet={isAzureDevOpsTokenSet}
            />
          )
        }
      />

      <SettingsInput
        key={azureDevOpsHostSet ?? "empty"}
        onChange={onAzureDevOpsHostChange || (() => {})}
        name="azure-devops-host-input"
        testId="azure-devops-host-input"
        label={t(I18nKey.GIT$AZURE_DEVOPS_HOST)}
        type="text"
        className="w-full max-w-[680px]"
        placeholder={t(I18nKey.GIT$AZURE_DEVOPS_HOST_PLACEHOLDER)}
        defaultValue={azureDevOpsHostSet || undefined}
        startContent={
          hasSavedOrg && (
            <KeyStatusIcon testId="azure-devops-set-host-indicator" isSet />
          )
        }
      />

      <AzureDevOpsTokenHelpAnchor />
    </div>
  );
}
