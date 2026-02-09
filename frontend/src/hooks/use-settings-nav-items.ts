import { useConfig } from "#/hooks/query/use-config";
import { SAAS_NAV_ITEMS, OSS_NAV_ITEMS } from "#/constants/settings-nav";

export function useSettingsNavItems() {
  const { data: config } = useConfig();

  const shouldHideLlmSettings = !!config?.feature_flags?.hide_llm_settings;
  const shouldHideBilling = !config?.feature_flags?.enable_billing;
  const isSaasMode = config?.app_mode === "saas";

  let items = isSaasMode ? SAAS_NAV_ITEMS : OSS_NAV_ITEMS;

  if (shouldHideLlmSettings) {
    items = items.filter((item) => item.to !== "/settings");
  }
  if (shouldHideBilling) {
    items = items.filter((item) => item.to !== "/settings/billing");
  }

  return items;
}
