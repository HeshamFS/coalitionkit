// SPDX-License-Identifier: Apache-2.0
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Card, DoorState, DraftReply } from "../genesis/api";
import { Join } from "../genesis/Join";
import { doorCodeIn, invitationIn } from "../landing/rooms";
import { Door } from "./Door";
import { Forming } from "./Forming";
import { pieces } from "./Sentence";

const GOAL = "Two members meet at Hall 3 by Friday.";

const seats: Card = {
  id: "seats",
  component: "SeatRing",
  title: "Seats",
  word: "Two members",
  size: "half",
  props: { goal: "", openSeats: 1, seats: [] },
};
const place: Card = {
  id: "place",
  component: "MapView",
  title: "Where",
  word: "Hall 3",
  size: "hero",
  props: { points: [] },
};

function draftReply(cards: Card[], over: Partial<DraftReply["draft"]> = {}): DraftReply {
  return {
    composition: { source: "reader", cards },
    draft: {
      goal: GOAL,
      roles: [{ id: "member", label: "member", count: 2 }],
      needs: [],
      deadline: "2031-06-06T21:59:59Z",
      deciders: "all",
      pack: null,
      place: "Hall 3",
      ...over,
    },
    source: "reader",
    reading: [],
  };
}

function door(over: Partial<DoorState> = {}): DoorState {
  return {
    code: "KT7-4QMZ",
    link: "http://127.0.0.1/join#KT7-4QMZ",
    stopped: false,
    visibility: "nearby",
    goal: GOAL,
    place: "Hall 3",
    closes_at: "2031-06-06T21:59:59Z",
    seats: 2,
    filled: 1,
    arrivals: [{ participant: "p1", role: "member", label: "member", home: "hosted", at: "t1" }],
    knocks: [],
    ...over,
  };
}

type Handler = (url: string, init?: RequestInit) => unknown;

function host(handler: Handler) {
  const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
    const body = handler(String(url), init);
    if (body instanceof Response) return body;
    return { ok: true, status: 200, json: async () => body } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  sessionStorage.clear();
  globalThis.history.replaceState(null, "", "/");
});

describe("the sentence", () => {
  it("cuts the goal into plain stretches and the words cards came from", () => {
    expect(pieces(GOAL, ["Hall 3", "Two members", "absent"])).toEqual([
      { text: "Two members", word: true },
      { text: " meet at ", word: false },
      { text: "Hall 3", word: true },
      { text: " by Friday.", word: false },
    ]);
  });
});

describe("room forming", () => {
  it("makes the sentence the headline and lights a card when its word is pointed at", async () => {
    host((url) => (url.includes("/v1/packs") ? [] : draftReply([place, seats])));
    render(<Forming onEnter={() => {}} initialGoal={GOAL} />);
    const word = await screen.findByRole("button", { name: "Hall 3" });
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(GOAL);
    const card = await screen.findByRole("region", { name: "Where" });
    await userEvent.hover(word);
    expect(card.getAttribute("data-hot")).toBe("true");
    await userEvent.unhover(word);
    expect(card.getAttribute("data-hot")).toBe("false");
  });

  it("draws different components for a different sentence, in the host's choice", async () => {
    host((url) => (url.includes("/v1/packs") ? [] : draftReply([seats], { place: null })));
    render(<Forming onEnter={() => {}} initialGoal={GOAL} />);
    await screen.findByRole("region", { name: "Seats" });
    expect(screen.queryByRole("region", { name: "Where" })).toBeNull();
  });

  it("changes the seats in place and counts them in the bar", async () => {
    host((url) => (url.includes("/v1/packs") ? [] : draftReply([seats])));
    render(<Forming onEnter={() => {}} initialGoal={GOAL} />);
    await userEvent.click(await screen.findByRole("button", { name: "One more member" }));
    expect(screen.getByText("3 seats")).toBeTruthy();
  });

  it("asks who can find it, then opens without a start code and shows the Door", async () => {
    const seen: { url: string; init?: RequestInit }[] = [];
    host((url, init) => {
      seen.push({ url, init });
      if (url.includes("/v1/packs")) return [];
      if (url.includes("/v1/genesis/draft")) return draftReply([seats]);
      if (url.includes("/v1/genesis/start")) {
        return {
          coalition_id: "c1",
          owner: { participant: "p1", token: "owner-token" },
          door: door(),
        };
      }
      return door();
    });
    render(<Forming onEnter={() => {}} initialGoal={GOAL} />);
    await userEvent.click(await screen.findByRole("button", { name: "Looks right" }));
    const near = screen.getByRole<HTMLInputElement>("radio", { name: /People nearby/ });
    expect(near.checked).toBe(true);
    expect(screen.getByText("What becomes public")).toBeTruthy();
    await userEvent.click(screen.getByRole("radio", { name: /Only with the code/ }));
    expect(screen.getByText("Nothing is listed")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Open the room" }));
    await screen.findByText("KT7-4QMZ");
    const start = seen.find((s) => s.url.includes("/v1/genesis/start"));
    expect(JSON.parse(String(start?.init?.body)).visibility).toBe("code");
    expect(
      (start?.init?.headers as Record<string, string> | undefined)?.authorization,
    ).toBeUndefined();
    expect(globalThis.location.pathname).toBe("/door");
  });

  it("offers no pin when the sentence names no place", async () => {
    host((url) => (url.includes("/v1/packs") ? [] : draftReply([seats], { place: null })));
    render(<Forming onEnter={() => {}} initialGoal={GOAL} />);
    await userEvent.click(await screen.findByRole("button", { name: "Looks right" }));
    expect(screen.getByRole<HTMLInputElement>("radio", { name: /People nearby/ }).disabled).toBe(
      true,
    );
    expect(
      screen.getByRole<HTMLInputElement>("radio", { name: /Only with the code/ }).checked,
    ).toBe(true);
  });

  it("says plainly when the host refuses to open", async () => {
    host((url) => {
      if (url.includes("/v1/packs")) return [];
      if (url.includes("/v1/genesis/start")) {
        return new Response(JSON.stringify({ detail: "" }), { status: 401 });
      }
      return draftReply([seats]);
    });
    render(<Forming onEnter={() => {}} initialGoal={GOAL} />);
    await userEvent.click(await screen.findByRole("button", { name: "Looks right" }));
    await userEvent.click(screen.getByRole("button", { name: "Open the room" }));
    expect((await screen.findByRole("alert")).textContent).toContain("needs a start link");
  });
});

describe("the Door", () => {
  it("shows the host's seats and arrivals, and answers a knock", async () => {
    const calls: string[] = [];
    host((url) => {
      calls.push(url);
      return url.includes("/knocks/")
        ? door({ filled: 2, knocks: [] })
        : door({ knocks: [{ id: "k1", at: "t2" }] });
    });
    render(<Door token="owner-token" onEnter={() => {}} />);
    expect(await screen.findByText("1 of 2 seats")).toBeTruthy();
    expect(screen.getByText("Muse, here in the browser")).toBeTruthy();
    await userEvent.click(await screen.findByRole("button", { name: "Let in" }));
    await waitFor(() => expect(calls.some((c) => c.includes("/knocks/k1"))).toBe(true));
    expect(await screen.findByText("2 of 2 seats")).toBeTruthy();
  });

  it("stops the code, and says what that means", async () => {
    let stopped = false;
    host((url) => {
      if (url.includes("/stop")) stopped = true;
      return door({ stopped });
    });
    render(<Door token="owner-token" first={door()} onEnter={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Stop this code" }));
    expect(await screen.findByText(/Nobody new can use this code/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Stop this code" })).toBeNull();
  });

  it("holds up only the QR, the code and the goal", async () => {
    host(() => door());
    render(<Door token="owner-token" first={door()} onEnter={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Hold up" }));
    expect(screen.queryByRole("region", { name: "Who has arrived" })).toBeNull();
    expect(screen.getByText("KT7-4QMZ")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Done" }));
    expect(screen.getByRole("region", { name: "Who has arrived" })).toBeTruthy();
  });
});

describe("arriving by code", () => {
  it("reads a spoken code in any case, with or without its dash", () => {
    expect(doorCodeIn("kt7-4qmz")).toBe("KT7-4QMZ");
    expect(doorCodeIn(" kt7 4qmz ")).toBe("KT7-4QMZ");
    expect(doorCodeIn("KT74QMZ")).toBe("KT7-4QMZ");
    expect(doorCodeIn("OI1-0000")).toBeNull();
    expect(invitationIn("http://127.0.0.1/join#KT7-4QMZ")).toBe("KT7-4QMZ");
  });

  it("shows the room and its open seats, and joins the chosen one", async () => {
    globalThis.history.replaceState(null, "", "/join#KT7-4QMZ");
    const sent: string[] = [];
    host((url, init) => {
      if (url.includes("/v1/door/join")) {
        sent.push(String(init?.body));
        return { coalition_id: "c1", participant: "p2", token: "member-token" };
      }
      return {
        goal: GOAL,
        place: null,
        closes_at: "2031-06-06T21:59:59Z",
        seats: 3,
        filled: 1,
        roles: [
          { id: "first", label: "First", open: 0 },
          { id: "second", label: "Second", open: 2 },
        ],
      };
    });
    const onJoined = vi.fn();
    render(<Join onJoined={onJoined} />);
    expect((await screen.findByRole("heading", { level: 1 })).textContent).toBe(GOAL);
    const group = await screen.findByRole("group", { name: "Which seat fits you?" });
    expect(within(group).getByRole<HTMLInputElement>("radio", { name: /Second/ }).checked).toBe(
      true,
    );
    await userEvent.click(screen.getByRole("button", { name: "Take a seat" }));
    await waitFor(() => expect(onJoined).toHaveBeenCalled());
    expect(JSON.parse(sent[0] ?? "{}")).toEqual({ code: "KT7-4QMZ", role: "second" });
  });

  it("says when a code has stopped working", async () => {
    globalThis.history.replaceState(null, "", "/join#KT7-4QMZ");
    host(() => new Response("{}", { status: 404 }));
    render(<Join onJoined={() => {}} />);
    expect((await screen.findByRole("alert")).textContent).toContain("stopped working");
  });
});
