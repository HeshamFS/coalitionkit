// SPDX-License-Identifier: Apache-2.0
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useSyncExternalStore,
} from "react";
import { type Answer, focusRequest } from "./actions";
import { AgentStore } from "./agent";
import type { HostConfig } from "./config";
import { type Fetch, openStream, postAnswer } from "./connection";
import { fixedFields } from "./derive";
import { FeedStore } from "./store";

export type FeedApi = {
  feed: FeedStore;
  agent: AgentStore;
  /** For trusted UI only: built from a host OpenRequest. */
  answer: (a: Answer) => Promise<void>;
  signOut: () => void;
};

const Ctx = createContext<FeedApi | null>(null);

export function useFeedApi(): FeedApi {
  const api = useContext(Ctx);
  if (!api) throw new Error("FeedProvider is missing");
  return api;
}

export const useFeedSnapshot = () => {
  const { feed } = useFeedApi();
  return useSyncExternalStore(feed.subscribe, feed.getSnapshot);
};
export const useAgentSnapshot = () => {
  const { agent } = useFeedApi();
  return useSyncExternalStore(agent.subscribe, agent.getSnapshot);
};

export function FeedProvider({
  config,
  fetchFn,
  delay,
  onSignedOut,
  children,
}: {
  config: HostConfig;
  fetchFn?: Fetch;
  delay?: (attempt: number) => number;
  /** The token was refused, or the viewer signed out. The caller clears it and shows sign-in. */
  onSignedOut?: (reason: "expired" | "signout") => void;
  children: ReactNode;
}) {
  const agent = useMemo(() => new AgentStore(), []);
  const answerRef = useRef<(a: Answer) => Promise<void>>(async () => {});
  const feed = useMemo(
    () =>
      new FeedStore((action) => {
        // A composed tree can only point at an open request; it can never answer one.
        const hit = focusRequest(action, agent.getSnapshot().requests);
        if (hit) agent.setFocus(hit.id);
      }),
    [agent],
  );

  const signedOut = useRef(onSignedOut);
  signedOut.current = onSignedOut;
  const expired = useCallback(() => signedOut.current?.("expired"), []);

  answerRef.current = async (a) => {
    const result = await postAnswer(config, a, fetchFn);
    if (!result.ok && result.auth) {
      expired();
      return;
    }
    agent.setRefusal(
      result.ok ? null : `${result.error}${result.detail ? `: ${result.detail}` : ""}`,
    );
  };

  useEffect(() => {
    const stopFeed = openStream({
      config,
      path: "/v1/feed",
      fetchFn,
      delay,
      onAuthError: expired,
      onEvent: (e) => {
        const keep = feed.handle(e);
        if (e.type === "STATE_SNAPSHOT" || e.type === "STATE_DELTA") {
          feed.book.setFallbackFields(fixedFields(feed.getSnapshot().state));
        }
        return keep;
      },
      onStatus: (s) => feed.setStatus(s),
    });
    const stopAgent = openStream({
      config,
      path: "/v1/agent",
      fetchFn,
      delay,
      onAuthError: expired,
      onEvent: (e) => agent.handle(e),
      onStatus: () => {},
    });
    return () => {
      stopFeed();
      stopAgent();
    };
  }, [config, fetchFn, delay, feed, agent, expired]);

  const api = useMemo<FeedApi>(
    () => ({
      feed,
      agent,
      answer: (a) => answerRef.current(a),
      signOut: () => signedOut.current?.("signout"),
    }),
    [feed, agent],
  );
  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}
