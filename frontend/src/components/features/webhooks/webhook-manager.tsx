import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FaTrash, FaPlus, FaChevronDown, FaChevronUp } from "react-icons/fa6";
import { I18nKey } from "#/i18n/declaration";
import { BrandButton } from "#/components/features/settings/brand-button";
import { SettingsInput } from "#/components/features/settings/settings-input";
import { LoadingSpinner } from "#/components/shared/loading-spinner";
import { useCurrentUser } from "#/hooks/query/use-current-user";
import { useOrganizations } from "#/hooks/query/use-organizations";
import {
  displayErrorToast,
  displaySuccessToast,
} from "#/utils/custom-toast-handlers";
import { openHands } from "#/api/open-hands-axios";

interface WebhookRule {
  id: string;
  webhook_config_id: string;
  event_type: string;
  conditions: Record<string, unknown> | null;
  action: string;
  priority: number;
  enabled: boolean;
}

interface WebhookConfig {
  id: string;
  organization_id: string;
  provider: string;
  repository_url: string;
  project_name: string | null;
  enabled: boolean;
  rules: WebhookRule[];
}

const EVENT_TYPE_OPTIONS = [
  { key: "pr_opened", label: "PR Opened" },
  { key: "pr_updated", label: "PR Updated" },
  { key: "pr_merged", label: "PR Merged" },
  { key: "push", label: "Push" },
  { key: "build_completed", label: "Build Completed" },
  { key: "work_item_created", label: "Work Item Created" },
  { key: "work_item_updated", label: "Work Item Updated" },
];

const ACTION_OPTIONS = [
  { key: "trigger_conversation", label: "Trigger Conversation" },
  { key: "ignore", label: "Ignore" },
];

function useWebhookConfigs(orgId: string | undefined) {
  return useQuery({
    queryKey: ["webhook-configs", orgId],
    queryFn: async (): Promise<WebhookConfig[]> => {
      if (!orgId) return [];
      const { data } = await openHands.get<WebhookConfig[]>(
        `/api/v1/webhooks/configs?organization_id=${orgId}`,
      );
      return data;
    },
    enabled: !!orgId,
  });
}

function AddRuleForm({
  configId,
  onCreated,
}: {
  configId: string;
  onCreated: () => void;
}) {
  const { t } = useTranslation();
  const [eventType, setEventType] = useState("pr_opened");
  const [action, setAction] = useState("trigger_conversation");
  const [priority, setPriority] = useState("0");
  const [conditions, setConditions] = useState("");

  const createRule = useMutation({
    mutationFn: async () => {
      let parsedConditions = null;
      if (conditions.trim()) {
        parsedConditions = JSON.parse(conditions);
      }
      await openHands.post(`/api/v1/webhooks/configs/${configId}/rules`, {
        event_type: eventType,
        action,
        priority: parseInt(priority, 10) || 0,
        conditions: parsedConditions,
      });
    },
    onSuccess: () => {
      displaySuccessToast(t(I18nKey.WEBHOOKS$RULE_CREATED));
      onCreated();
      setConditions("");
    },
    onError: () => displayErrorToast("Failed to create rule"),
  });

  return (
    <div className="border border-tertiary rounded-md p-4 flex flex-col gap-3">
      <div className="flex gap-3 flex-wrap">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">
            {t(I18nKey.WEBHOOKS$EVENT_TYPE)}
          </label>
          <select
            value={eventType}
            onChange={(e) => setEventType(e.target.value)}
            className="bg-base-tertiary text-white rounded px-3 py-1.5 text-sm"
          >
            {EVENT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.key} value={opt.key}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-neutral-400">
            {t(I18nKey.WEBHOOKS$ACTION)}
          </label>
          <select
            value={action}
            onChange={(e) => setAction(e.target.value)}
            className="bg-base-tertiary text-white rounded px-3 py-1.5 text-sm"
          >
            {ACTION_OPTIONS.map((opt) => (
              <option key={opt.key} value={opt.key}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1 w-20">
          <label className="text-xs text-neutral-400">
            {t(I18nKey.WEBHOOKS$PRIORITY)}
          </label>
          <input
            type="number"
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            className="bg-base-tertiary text-white rounded px-3 py-1.5 text-sm w-full"
          />
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-xs text-neutral-400">
          {t(I18nKey.WEBHOOKS$CONDITIONS)}
        </label>
        <textarea
          value={conditions}
          onChange={(e) => setConditions(e.target.value)}
          placeholder='{"draft": {"equals": false}}'
          className="bg-base-tertiary text-white rounded px-3 py-2 text-sm font-mono min-h-[60px] resize-y"
        />
      </div>
      <BrandButton
        type="button"
        variant="primary"
        onClick={() => createRule.mutate()}
        isDisabled={createRule.isPending}
      >
        {createRule.isPending ? (
          <LoadingSpinner size="small" />
        ) : (
          t(I18nKey.WEBHOOKS$ADD_RULE)
        )}
      </BrandButton>
    </div>
  );
}

function WebhookConfigCard({
  config,
  isAdmin,
}: {
  config: WebhookConfig;
  isAdmin: boolean;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [showAddRule, setShowAddRule] = useState(false);

  const deleteConfig = useMutation({
    mutationFn: () => openHands.delete(`/api/v1/webhooks/configs/${config.id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhook-configs"] });
      displaySuccessToast(t(I18nKey.WEBHOOKS$CONFIG_DELETED));
    },
    onError: () => displayErrorToast("Failed to delete config"),
  });

  const deleteRule = useMutation({
    mutationFn: (ruleId: string) =>
      openHands.delete(`/api/v1/webhooks/configs/${config.id}/rules/${ruleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["webhook-configs"] });
      displaySuccessToast(t(I18nKey.WEBHOOKS$RULE_DELETED));
    },
    onError: () => displayErrorToast("Failed to delete rule"),
  });

  const toggleEnabled = useMutation({
    mutationFn: () =>
      openHands.put(`/api/v1/webhooks/configs/${config.id}`, {
        enabled: !config.enabled,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["webhook-configs"] }),
  });

  return (
    <div className="border border-tertiary rounded-md overflow-hidden">
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-base-tertiary/50"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span
            className={`w-2 h-2 rounded-full ${config.enabled ? "bg-green-500" : "bg-neutral-500"}`}
          />
          <div>
            <p className="text-sm font-medium text-white">
              {config.project_name || config.repository_url}
            </p>
            <p className="text-xs text-neutral-400">{config.repository_url}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-neutral-400">
            {t(I18nKey.WEBHOOKS$RULE_COUNT, { count: config.rules.length })}
          </span>
          {expanded ? <FaChevronUp size={12} /> : <FaChevronDown size={12} />}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-tertiary p-4 flex flex-col gap-4">
          {isAdmin && (
            <div className="flex items-center gap-3">
              <BrandButton
                type="button"
                variant="secondary"
                onClick={() => toggleEnabled.mutate()}
              >
                {config.enabled
                  ? t(I18nKey.WEBHOOKS$DISABLE)
                  : t(I18nKey.WEBHOOKS$ENABLE)}
              </BrandButton>
              <BrandButton
                type="button"
                variant="secondary"
                onClick={() => deleteConfig.mutate()}
                isDisabled={deleteConfig.isPending}
              >
                {t(I18nKey.WEBHOOKS$DELETE)}
              </BrandButton>
            </div>
          )}

          <div>
            <h4 className="text-sm font-medium text-white mb-2">
              {t(I18nKey.WEBHOOKS$RULES)}
            </h4>
            {config.rules.length === 0 ? (
              <p className="text-xs text-neutral-400">
                {t(I18nKey.WEBHOOKS$NO_RULES)}
              </p>
            ) : (
              <div className="flex flex-col gap-2">
                {config.rules.map((rule) => (
                  <div
                    key={rule.id}
                    className="flex items-center justify-between bg-base-tertiary rounded px-3 py-2"
                  >
                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-white font-mono">
                        {rule.event_type}
                      </span>
                      <span
                        className={
                          rule.action === "trigger_conversation"
                            ? "text-green-400"
                            : "text-neutral-400"
                        }
                      >
                        {rule.action === "trigger_conversation"
                          ? t(I18nKey.WEBHOOKS$TRIGGER)
                          : t(I18nKey.WEBHOOKS$IGNORE)}
                      </span>
                      <span className="text-neutral-500 text-xs">
                        {t(I18nKey.WEBHOOKS$PRIORITY_LABEL, {
                          value: rule.priority,
                        })}
                      </span>
                      {rule.conditions && (
                        <span className="text-neutral-500 text-xs font-mono truncate max-w-[200px]">
                          {JSON.stringify(rule.conditions)}
                        </span>
                      )}
                    </div>
                    {isAdmin && (
                      <button
                        type="button"
                        onClick={() => deleteRule.mutate(rule.id)}
                        className="text-neutral-400 hover:text-red-400 cursor-pointer"
                      >
                        <FaTrash size={12} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {isAdmin && (
            <div>
              {showAddRule ? (
                <AddRuleForm
                  configId={config.id}
                  onCreated={() => {
                    queryClient.invalidateQueries({
                      queryKey: ["webhook-configs"],
                    });
                    setShowAddRule(false);
                  }}
                />
              ) : (
                <BrandButton
                  type="button"
                  variant="secondary"
                  onClick={() => setShowAddRule(true)}
                >
                  <FaPlus size={10} className="mr-1" />
                  {t(I18nKey.WEBHOOKS$ADD_RULE)}
                </BrandButton>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AddConfigForm({
  orgId,
  onCreated,
}: {
  orgId: string;
  onCreated: () => void;
}) {
  const { t } = useTranslation();
  const [repoUrl, setRepoUrl] = useState("");
  const [projectName, setProjectName] = useState("");

  const createConfig = useMutation({
    mutationFn: async () => {
      await openHands.post("/api/v1/webhooks/configs", {
        organization_id: orgId,
        provider: "azure_devops",
        repository_url: repoUrl,
        project_name: projectName || null,
      });
    },
    onSuccess: () => {
      displaySuccessToast(t(I18nKey.WEBHOOKS$CONFIG_CREATED));
      onCreated();
      setRepoUrl("");
      setProjectName("");
    },
    onError: () => displayErrorToast("Failed to create webhook config"),
  });

  return (
    <div className="border border-tertiary rounded-md p-4 flex flex-col gap-3">
      <SettingsInput
        testId="webhook-repo-url"
        label={t(I18nKey.WEBHOOKS$REPOSITORY_URL)}
        type="text"
        value={repoUrl}
        onChange={setRepoUrl}
        placeholder="https://dev.azure.com/org/project/_git/repo"
      />
      <SettingsInput
        testId="webhook-project-name"
        label={t(I18nKey.WEBHOOKS$PROJECT_NAME)}
        type="text"
        value={projectName}
        onChange={setProjectName}
        placeholder="MyProject"
      />
      <BrandButton
        type="button"
        variant="primary"
        onClick={() => createConfig.mutate()}
        isDisabled={createConfig.isPending || !repoUrl.trim()}
      >
        {createConfig.isPending ? (
          <LoadingSpinner size="small" />
        ) : (
          t(I18nKey.WEBHOOKS$ADD_CONFIG)
        )}
      </BrandButton>
    </div>
  );
}

export function WebhookManager() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const { data: currentUser } = useCurrentUser();
  const { data: organizations } = useOrganizations();
  const orgId = organizations?.[0]?.id;
  const isAdmin = currentUser?.is_org_admin ?? false;

  const { data: configs = [], isLoading } = useWebhookConfigs(orgId);

  const [showAddForm, setShowAddForm] = useState(false);

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="large" />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {!isAdmin && (
        <div className="bg-amber-900/30 border border-amber-700 rounded-md px-4 py-3 text-sm text-amber-200">
          {t(I18nKey.WEBHOOKS$ADMIN_ONLY)}
        </div>
      )}

      {isAdmin && (
        <div>
          {showAddForm ? (
            <AddConfigForm
              orgId={orgId!}
              onCreated={() => {
                queryClient.invalidateQueries({
                  queryKey: ["webhook-configs"],
                });
                setShowAddForm(false);
              }}
            />
          ) : (
            <BrandButton
              type="button"
              variant="primary"
              onClick={() => setShowAddForm(true)}
            >
              <FaPlus size={10} className="mr-1" />
              {t(I18nKey.WEBHOOKS$ADD_CONFIG)}
            </BrandButton>
          )}
        </div>
      )}

      {configs.length === 0 ? (
        <p className="text-sm text-neutral-400">
          {t(I18nKey.WEBHOOKS$NO_CONFIGS)}
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {configs.map((config) => (
            <WebhookConfigCard
              key={config.id}
              config={config}
              isAdmin={isAdmin}
            />
          ))}
        </div>
      )}
    </div>
  );
}
