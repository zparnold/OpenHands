import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { useTranslation } from "react-i18next";
import { completeEntraPkceLogin } from "#/hooks/use-entra-pkce-login";
import { I18nKey } from "#/i18n/declaration";
import {
  setAccessToken,
  setLoginMethod,
  LoginMethod,
} from "#/utils/local-storage";

const EXCHANGE_FLAG = "entra_pkce_exchanging";

/**
 * OAuth callback for Microsoft Entra ID PKCE (SPA) flow.
 * Exchanges the authorization code directly with Entra - no backend involved.
 *
 * Uses sessionStorage + immediate URL replacement to prevent double exchange
 * (React Strict Mode, HMR, or remounts can run the effect twice; the code is single-use).
 */
export default function OAuthEntraCallback() {
  const { t } = useTranslation();
  const [searchParams] = useSearchParams();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const alreadyExchanging = sessionStorage.getItem(EXCHANGE_FLAG) === "1";

    if (!code) {
      if (alreadyExchanging) return;
      setError("No authorization code received");
      return;
    }
    if (!state) {
      setError("No PKCE state found - please try logging in again");
      return;
    }
    if (alreadyExchanging) return;

    sessionStorage.setItem(EXCHANGE_FLAG, "1");
    window.history.replaceState({}, document.title, window.location.pathname);

    completeEntraPkceLogin(code, state)
      .then(({ accessToken, returnTo }) => {
        setAccessToken(accessToken);
        setLoginMethod(LoginMethod.ENTERPRISE_SSO);
        sessionStorage.removeItem(EXCHANGE_FLAG);
        window.location.href = returnTo || "/";
      })
      .catch((err) => {
        setError(err?.message || "Token exchange failed");
      })
      .finally(() => {
        sessionStorage.removeItem(EXCHANGE_FLAG);
      });
  }, [searchParams]);

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-base p-4">
        <p className="text-danger text-center mb-4">{error}</p>
        <a href="/login" className="text-primary hover:underline">
          {t(I18nKey.INVITE$RETURN_TO_LOGIN)}
        </a>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-base">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white" />
    </div>
  );
}
