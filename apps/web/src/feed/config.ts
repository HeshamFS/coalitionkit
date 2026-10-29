// SPDX-License-Identifier: Apache-2.0
// Where the host is and who the viewer is.
//
// Two rules keep the bearer token from reaching the wrong server:
//  1. The server origin comes only from build-time config (VITE_CK_HOST) or is the page origin.
//     A `host` query parameter is honoured only when its origin is on the build-time allowlist
//     (VITE_CK_ALLOWED_HOSTS, comma separated); anything else is refused.
//  2. The token is never read from the address. It comes from the sign-in step, lives in memory
//     and sessionStorage, and is sent only to the allowed origin.

export type HostConfig = { baseUrl: string; token: string };

export type BuildEnv = { VITE_CK_HOST?: string; VITE_CK_ALLOWED_HOSTS?: string };

const KEY = "ck.token";
let memoryToken = "";

function originOf(value: string): string | null {
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.origin : null;
  } catch {
    return null;
  }
}

export function allowedOrigins(env: BuildEnv): string[] {
  const list = [env.VITE_CK_HOST, ...(env.VITE_CK_ALLOWED_HOSTS ?? "").split(",")];
  return list.map((v) => originOf((v ?? "").trim())).filter((v): v is string => v !== null);
}

/** "" means same origin. Otherwise an origin from the allowlist, never from the address. */
export function resolveBase(search: string, env: BuildEnv): string {
  const allowed = allowedOrigins(env);
  const fixed = originOf(env.VITE_CK_HOST ?? "") ?? "";
  const asked = new URLSearchParams(search).get("host");
  if (asked) {
    const origin = originOf(asked);
    if (origin && allowed.includes(origin)) return origin;
  }
  return fixed;
}

/** Throws unless sending the token to this base is allowed. Called before every request. */
export function assertAllowedBase(baseUrl: string, env: BuildEnv = import.meta.env): void {
  if (baseUrl === "") return;
  const origin = originOf(baseUrl);
  if (!origin || !allowedOrigins(env).includes(origin)) {
    throw new Error("refusing to send credentials to an origin that is not allowed");
  }
}

function safeStorage(): Storage | undefined {
  try {
    return globalThis.sessionStorage;
  } catch {
    return undefined;
  }
}

export function saveToken(token: string): void {
  memoryToken = token;
  safeStorage()?.setItem(KEY, token);
}

export function clearToken(): void {
  memoryToken = "";
  safeStorage()?.removeItem(KEY);
}

/** Drop a `token` parameter from the address without reading it. */
export function scrubAddress(): void {
  const url = new URL(globalThis.location.href);
  if (!url.searchParams.has("token")) return;
  url.searchParams.delete("token");
  globalThis.history.replaceState(null, "", url.toString());
}

export function readConfig(
  search: string = globalThis.location?.search ?? "",
  env: BuildEnv = import.meta.env,
): HostConfig | null {
  const token = memoryToken || safeStorage()?.getItem(KEY) || "";
  if (!token) return null;
  return { baseUrl: resolveBase(search, env), token };
}
