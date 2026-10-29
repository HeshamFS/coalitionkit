// SPDX-License-Identifier: Apache-2.0
// /confirm/<code>: the page a message link opens. After sign-in it redeems the one-time code with
// the host and shows the existing trusted request card for that subject. There is no signing path
// here: the answer goes through the same trusted answer flow as every other consent.
import { useEffect, useState } from "react";
import { Banner, Skeleton } from "./components/feedback";
import type { OpenRequest } from "./feed/agent";
import type { HostConfig } from "./feed/config";
import { type Fetch, type RedeemFailure, redeemConfirm } from "./feed/connection";
import { useFeedApi, useFeedSnapshot } from "./feed/useFeed";
import { TrustedRequest } from "./TrustedRequest";

export const CONFIRM_PREFIX = "/confirm/";

/** The code in a /confirm/<code> address, or null. */
export function confirmCode(pathname: string): string | null {
  if (!pathname.startsWith(CONFIRM_PREFIX)) return null;
  const code = decodeURIComponent(pathname.slice(CONFIRM_PREFIX.length)).trim();
  return code && !code.includes("/") ? code : null;
}

export const FAILURE_TEXT: Record<RedeemFailure, string> = {
  unauthorized: "Your session ended. Sign in again.",
  unknown: "This confirm link is not valid.",
  expired: "This confirm link expired. Ask for a new one in your chat.",
  used: "This confirm link was already used, or the request changed. Ask for a new one.",
  other_person: "This confirm link belongs to someone else.",
  failed: "The confirm link could not be checked. Try again.",
};

// A code works once, so a re-render (React strict mode runs effects twice) must reuse the first
// attempt instead of spending the code a second time. Attempts are kept per host, session and
// code: an attempt refused for an ended session is dropped, so signing in again can retry.
const attempts = new Map<string, ReturnType<typeof redeemConfirm>>();

function attemptKey(config: HostConfig, code: string): string {
  return `${config.baseUrl}\n${config.token}\n${code}`;
}

type View =
  | { step: "checking" }
  | { step: "failed"; reason: RedeemFailure }
  | { step: "ask"; request: OpenRequest }
  | { step: "sent" };

export function ConfirmRoute({
  code,
  config,
  fetchFn,
}: {
  code: string;
  config: HostConfig;
  fetchFn?: Fetch;
}) {
  const { answer, agent, signOut } = useFeedApi();
  const feed = useFeedSnapshot();
  const [view, setView] = useState<View>({ step: "checking" });

  useEffect(() => {
    let live = true;
    const key = attemptKey(config, code);
    let attempt = attempts.get(key);
    if (!attempt) {
      attempt = redeemConfirm(config, code, fetchFn).catch(() => ({
        ok: false as const,
        reason: "failed" as const,
      }));
      attempts.set(key, attempt);
    }
    void attempt.then((result) => {
      if (!live) return;
      if (!result.ok && result.reason === "unauthorized") {
        // The host never checked the code: keep it in the address and let a new session retry.
        attempts.delete(key);
        signOut();
        return;
      }
      // The host decided on the code: take it out of the address.
      globalThis.history?.replaceState(null, "", CONFIRM_PREFIX);
      if (result.ok) setView({ step: "ask", request: result.request });
      else setView({ step: "failed", reason: result.reason });
    });
    return () => {
      live = false;
    };
  }, [code, config, fetchFn, signOut]);

  if (view.step === "checking") return <Skeleton shape="card" label="Checking your confirm link" />;
  if (view.step === "failed") {
    return (
      <Banner
        tone="blocked"
        title="Could not open this request."
        body={FAILURE_TEXT[view.reason]}
      />
    );
  }
  if (view.step === "sent") {
    return <Banner tone="agreed" title="Sent." body="You can go back to your chat." />;
  }
  return (
    <>
      {agent.getSnapshot().refusal && (
        <Banner
          tone="blocked"
          title="The host did not take that answer."
          body={agent.getSnapshot().refusal ?? ""}
        />
      )}
      <TrustedRequest
        request={view.request}
        state={feed.state}
        onAnswer={(a) =>
          void answer(a).then(() => {
            if (agent.getSnapshot().refusal === null) setView({ step: "sent" });
          })
        }
      />
    </>
  );
}
