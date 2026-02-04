/**
 * PKCE (Proof Key for Code Exchange) for Microsoft Entra ID SPA auth.
 * Frontend handles the full OAuth flow - no backend token exchange needed.
 * No client_secret required; Azure app must be configured as SPA.
 *
 * The code_verifier is encoded in the OAuth state param (not sessionStorage)
 * so it survives redirects across origins (e.g. localhost vs 127.0.0.1).
 */

function base64UrlEncode(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

async function sha256(plain: string): Promise<ArrayBuffer> {
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);
  return crypto.subtle.digest("SHA-256", data);
}

/**
 * Generate code_verifier and code_challenge for PKCE.
 */
export async function generatePkcePair(): Promise<{
  codeVerifier: string;
  codeChallenge: string;
}> {
  const randomBytes = new Uint8Array(32);
  crypto.getRandomValues(randomBytes);
  const codeVerifier = base64UrlEncode(randomBytes.buffer);

  const hashed = await sha256(codeVerifier);
  const codeChallenge = base64UrlEncode(hashed);

  return { codeVerifier, codeChallenge };
}

/** Payload encoded in OAuth state - survives redirect (no sessionStorage). */
export interface StatePayload {
  codeVerifier: string;
  returnTo: string;
}

/** Encode code_verifier + returnTo into OAuth state param. */
export function encodeStatePayload(
  codeVerifier: string,
  returnTo: string,
): string {
  const payload: StatePayload = { codeVerifier, returnTo };
  const json = JSON.stringify(payload);
  return btoa(json).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/** Decode OAuth state param back to code_verifier and returnTo. */
export function decodeStatePayload(state: string): StatePayload {
  const padded = state.replace(/-/g, "+").replace(/_/g, "/");
  const json = atob(padded);
  const payload = JSON.parse(json) as StatePayload;
  if (!payload.codeVerifier || typeof payload.returnTo !== "string") {
    throw new Error("Invalid state payload");
  }
  return payload;
}

/**
 * Build Entra authorize URL with PKCE.
 */
export function buildEntraAuthorizeUrl(params: {
  tenantId: string;
  clientId: string;
  redirectUri: string;
  codeChallenge: string;
  state: string;
}): string {
  const searchParams = new URLSearchParams({
    client_id: params.clientId,
    response_type: "code",
    redirect_uri: params.redirectUri,
    scope: "openid email profile",
    response_mode: "query",
    code_challenge: params.codeChallenge,
    code_challenge_method: "S256",
    state: params.state,
  });
  return `https://login.microsoftonline.com/${params.tenantId}/oauth2/v2.0/authorize?${searchParams.toString()}`;
}

/**
 * Exchange authorization code for tokens at Entra (no backend, no client_secret).
 * Returns id_token for backend validation (audience = our client ID).
 * access_token is for Microsoft Graph; id_token is for our API.
 */
export async function exchangeCodeForToken(params: {
  tenantId: string;
  clientId: string;
  redirectUri: string;
  code: string;
  codeVerifier: string;
}): Promise<{ id_token: string; access_token: string; token_type: string }> {
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: params.clientId,
    redirect_uri: params.redirectUri,
    code: params.code,
    code_verifier: params.codeVerifier,
  });

  const response = await fetch(
    `https://login.microsoftonline.com/${params.tenantId}/oauth2/v2.0/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
    },
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Token exchange failed: ${text}`);
  }

  const data = (await response.json()) as {
    access_token?: string;
    id_token?: string;
    token_type?: string;
  };
  if (!data.access_token) {
    throw new Error("No access_token in response");
  }
  if (!data.id_token) {
    throw new Error("No id_token in response (ensure openid scope)");
  }

  return {
    id_token: data.id_token,
    access_token: data.access_token,
    token_type: data.token_type || "Bearer",
  };
}
