const hostedUiConfig = {
  region: process.env.NEXT_PUBLIC_COGNITO_REGION,
  userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
  clientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
  domain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN,
};

export const ID_TOKEN_STORAGE_KEY = "tracevault.id_token";
export const TENANT_STORAGE_KEY = "tracevault.tenant";

export function hasHostedUiConfig(): boolean {
  return Boolean(
    hostedUiConfig.region &&
      hostedUiConfig.userPoolId &&
      hostedUiConfig.clientId &&
      hostedUiConfig.domain,
  );
}

export function buildHostedUiUrl(redirectUri: string): string {
  const domain = hostedUiConfig.domain;
  const clientId = hostedUiConfig.clientId;

  if (!domain || !clientId) {
    return "";
  }

  const url = new URL(`https://${domain}/oauth2/authorize`);
  url.searchParams.set("identity_provider", "COGNITO");
  url.searchParams.set("response_type", "token");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("scope", "openid profile email");

  return url.toString();
}

export function persistIdTokenFromHash(): void {
  if (typeof window === "undefined") {
    return;
  }

  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : window.location.hash;
  const params = new URLSearchParams(hash);
  const idToken = params.get("id_token");

  if (!idToken) {
    return;
  }

  window.sessionStorage.setItem(ID_TOKEN_STORAGE_KEY, idToken);
  window.history.replaceState(
    null,
    "",
    `${window.location.pathname}${window.location.search}`,
  );
}
