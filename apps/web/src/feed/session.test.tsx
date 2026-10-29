// SPDX-License-Identifier: Apache-2.0
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { HostConfig } from "./config";
import type { Fetch } from "./connection";
import { type FeedApi, FeedProvider, useFeedApi } from "./useFeed";

const config: HostConfig = { baseUrl: "", token: "token-a" };

function Grab({ into }: { into: (api: FeedApi) => void }) {
  into(useFeedApi());
  return null;
}

describe("a late answer from an earlier session", () => {
  it("never signs out the session that replaced it", async () => {
    let release: (r: Response) => void = () => {};
    const fetchFn: Fetch = vi.fn((url: string) => {
      if (String(url).endsWith("/v1/agent/answers")) {
        return new Promise<Response>((resolve) => {
          release = resolve;
        });
      }
      return new Promise<Response>(() => {}); // streams stay open
    }) as unknown as Fetch;
    const onSignedOut = vi.fn();
    let api: FeedApi | null = null;
    const view = render(
      <FeedProvider config={config} fetchFn={fetchFn} onSignedOut={onSignedOut}>
        <Grab into={(a) => (api = a)} />
      </FeedProvider>,
    );
    const pending = (api as unknown as FeedApi).answer({
      interrupt_id: "plan:p1:2:u1",
      consent: true,
    });
    view.unmount(); // the viewer signed in again; this provider is gone
    release(new Response("{}", { status: 401 }));
    await pending;
    expect(onSignedOut).not.toHaveBeenCalled();
  });
});
