import { Provider } from "#/types/settings";

export interface WebClientFeatureFlags {
  enable_billing: boolean;
  hide_llm_settings: boolean;
  enable_jira: boolean;
  enable_jira_dc: boolean;
  enable_linear: boolean;
}

export interface WebClientConfig {
  app_mode: "saas" | "oss";
  posthog_client_key: string | null;
  feature_flags: WebClientFeatureFlags;
  providers_configured: Provider[];
  maintenance_start_time: string | null;
  auth_url: string | null;
  recaptcha_site_key: string | null;
  faulty_models: string[];
  error_message: string | null;
  updated_at: string;
  github_app_slug: string | null;
  /** Git providers to show in integrations (self-hosted). If empty/undefined, all are shown. */
  git_providers_enabled?: string[];
  /** Entra PKCE (SPA) - no client_secret needed. Required for enterprise_sso login. */
  entra_tenant_id?: string | null;
  entra_client_id?: string | null;
}
