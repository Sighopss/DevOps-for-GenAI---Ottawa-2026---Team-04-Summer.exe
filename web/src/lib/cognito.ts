import type { TenantId } from "@/lib/types";

const hostedUiConfig = {
  region: process.env.NEXT_PUBLIC_COGNITO_REGION,
  userPoolId: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
  clientId: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
  domain: process.env.NEXT_PUBLIC_COGNITO_DOMAIN,
};

export const ID_TOKEN_STORAGE_KEY = "tracevault.id_token";
export const TENANT_STORAGE_KEY = "tracevault.tenant";
const CODE_VERIFIER_STORAGE_KEY = "tracevault.code_verifier";
const OAUTH_STATE_STORAGE_KEY = "tracevault.oauth_state";

type StoredIdentity = {
  tenantId: TenantId | null;
  username: string | null;
};

export function hasHostedUiConfig(): boolean {
  return Boolean(
    hostedUiConfig.region &&
      hostedUiConfig.userPoolId &&
      hostedUiConfig.clientId &&
      hostedUiConfig.domain,
  );
}

function encodeBase64Url(bytes: Uint8Array): string {
  const binary = Array.from(bytes, (byte) => String.fromCharCode(byte)).join("");
  return window
    .btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
}

async function sha256Base64Url(value: string): Promise<string> {
  const digest = await window.crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(value),
  );
  return encodeBase64Url(new Uint8Array(digest));
}

function createRandomVerifier(length = 32): string {
  const bytes = new Uint8Array(length);
  window.crypto.getRandomValues(bytes);
  return encodeBase64Url(bytes);
}

export async function buildHostedUiUrl(redirectUri: string): Promise<string> {
  const domain = hostedUiConfig.domain;
  const clientId = hostedUiConfig.clientId;

  if (!domain || !clientId || typeof window === "undefined") {
    return "";
  }

  const codeVerifier = createRandomVerifier();
  const state = createRandomVerifier(24);
  const codeChallenge = await sha256Base64Url(codeVerifier);

  window.sessionStorage.setItem(CODE_VERIFIER_STORAGE_KEY, codeVerifier);
  window.sessionStorage.setItem(OAUTH_STATE_STORAGE_KEY, state);

  const url = new URL(`https://${domain}/oauth2/authorize`);
  url.searchParams.set("identity_provider", "COGNITO");
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirectUri);
  url.searchParams.set("scope", "openid profile email");
  url.searchParams.set("state", state);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("code_challenge", codeChallenge);

  return url.toString();
}

export function readStoredIdToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.sessionStorage.getItem(ID_TOKEN_STORAGE_KEY);
}

function clearHostedUiTransientState(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(CODE_VERIFIER_STORAGE_KEY);
  window.sessionStorage.removeItem(OAUTH_STATE_STORAGE_KEY);
}

function cleanCurrentUrl(nextUrl?: string): void {
  window.history.replaceState(
    null,
    "",
    nextUrl ?? `${window.location.pathname}${window.location.search}`,
  );
}

async function exchangeAuthorizationCode(code: string, redirectUri: string): Promise<string> {
  const domain = hostedUiConfig.domain;
  const clientId = hostedUiConfig.clientId;
  const codeVerifier = window.sessionStorage.getItem(CODE_VERIFIER_STORAGE_KEY);

  if (!domain || !clientId || !codeVerifier) {
    throw new Error("Hosted UI code exchange is not configured.");
  }

  const response = await fetch(`https://${domain}/oauth2/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      client_id: clientId,
      code,
      redirect_uri: redirectUri,
      code_verifier: codeVerifier,
    }).toString(),
  });

  if (!response.ok) {
    throw new Error("Cognito token exchange failed.");
  }

  const body = (await response.json()) as { id_token?: string };
  if (!body.id_token) {
    throw new Error("Cognito did not return an ID token.");
  }

  return body.id_token;
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
  cleanCurrentUrl();
}

export async function completeHostedUiSignIn(): Promise<boolean> {
  if (typeof window === "undefined") {
    return false;
  }

  persistIdTokenFromHash();
  if (readStoredIdToken()) {
    return true;
  }

  const currentUrl = new URL(window.location.href);
  const code = currentUrl.searchParams.get("code");
  if (!code) {
    return false;
  }

  const expectedState = window.sessionStorage.getItem(OAUTH_STATE_STORAGE_KEY);
  const returnedState = currentUrl.searchParams.get("state");
  if (!expectedState || !returnedState || expectedState !== returnedState) {
    clearHostedUiTransientState();
    throw new Error("Cognito state verification failed.");
  }

  const idToken = await exchangeAuthorizationCode(code, window.location.origin);
  window.sessionStorage.setItem(ID_TOKEN_STORAGE_KEY, idToken);
  clearHostedUiTransientState();
  currentUrl.searchParams.delete("code");
  currentUrl.searchParams.delete("state");
  cleanCurrentUrl(`${currentUrl.pathname}${currentUrl.search}`);
  return true;
}

function decodeBase64Url(segment: string): string {
  const normalized = segment.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  return window.atob(padded);
}

export function readIdTokenIdentity(idToken: string | null): StoredIdentity {
  if (!idToken || typeof window === "undefined") {
    return { tenantId: null, username: null };
  }

  try {
    const [, payload] = idToken.split(".");
    if (!payload) {
      return { tenantId: null, username: null };
    }

    const parsed = JSON.parse(decodeBase64Url(payload)) as {
      "custom:tenant_id"?: string;
      "cognito:username"?: string;
      username?: string;
    };

    return {
      tenantId:
        parsed["custom:tenant_id"] === "tenant-a" || parsed["custom:tenant_id"] === "tenant-b"
          ? parsed["custom:tenant_id"]
          : null,
      username: parsed["cognito:username"] ?? parsed.username ?? null,
    };
  } catch {
    return { tenantId: null, username: null };
  }
}
