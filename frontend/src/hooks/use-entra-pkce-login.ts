import { useCallback } from "react";
import OptionService from "#/api/option-service/option-service.api";
import { useConfig } from "./query/use-config";
import {
  buildEntraAuthorizeUrl,
  decodeStatePayload,
  encodeStatePayload,
  exchangeCodeForToken,
  generatePkcePair,
} from "#/utils/entra-pkce";

/**
 * Hook for Microsoft Entra ID PKCE (SPA) login.
 * Frontend handles the full OAuth flow - no backend token exchange.
 * Requires ENTRA_TENANT_ID and ENTRA_CLIENT_ID in config.
 */
export function useEntraPkceLogin(returnTo = "/") {
  const { data: config } = useConfig();

  const handleLogin = useCallback(async () => {
    const tenantId = config?.ENTRA_TENANT_ID;
    const clientId = config?.ENTRA_CLIENT_ID;

    if (!tenantId || !clientId) {
      return;
    }

    const redirectUri = `${window.location.origin}/oauth/entra/callback`;
    const { codeVerifier, codeChallenge } = await generatePkcePair();
    const state = encodeStatePayload(codeVerifier, returnTo);

    const url = buildEntraAuthorizeUrl({
      tenantId,
      clientId,
      redirectUri,
      codeChallenge,
      state,
    });

    window.location.href = url;
  }, [config?.ENTRA_TENANT_ID, config?.ENTRA_CLIENT_ID, returnTo]);

  return {
    handleLogin,
    isConfigured: !!(config?.ENTRA_TENANT_ID && config?.ENTRA_CLIENT_ID),
  };
}

/**
 * Exchange the authorization code for tokens (call from callback route).
 * State comes from the URL (Entra echoes it back) - no sessionStorage needed.
 * Returns id_token for backend validation (audience = our client ID).
 */
export async function completeEntraPkceLogin(
  code: string,
  state: string,
): Promise<{ accessToken: string; returnTo: string }> {
  if (!state) {
    throw new Error("No PKCE state found - please try logging in again");
  }

  const payload = decodeStatePayload(state);

  const config = await OptionService.getConfig();
  const tenantId = config.ENTRA_TENANT_ID;
  const clientId = config.ENTRA_CLIENT_ID;

  if (!tenantId || !clientId) {
    throw new Error("Entra ID not configured");
  }

  const redirectUri = `${window.location.origin}/oauth/entra/callback`;
  const { id_token: idToken } = await exchangeCodeForToken({
    tenantId,
    clientId,
    redirectUri,
    code,
    codeVerifier: payload.codeVerifier,
  });

  return { accessToken: idToken, returnTo: payload.returnTo };
}
