// SPDX-License-Identifier: Apache-2.0
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";
import { applyStoredTheme, chooseTheme, storedTheme } from "../shell/theme";
import { Landing } from "./Landing";
import { invitationIn, type Room, spots } from "./rooms";

const SECRET = "abcdefghijklmnop1234";

function room(over: Partial<Room> = {}): Room {
  return {
    id: "r1",
    goal: "Goal one",
    seats: 4,
    filled: 1,
    closes: "closes soon",
    lat: 1,
    lon: 1,
    status: "forming",
    sample: true,
    ...over,
  };
}

function hostAnswers(body: unknown, ok = true) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok, json: async () => body })),
  );
}

beforeEach(() => {
  history.replaceState(null, "", "/");
  sessionStorage.clear();
  localStorage.clear();
  document.documentElement.dataset.theme = "light";
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("Landing", () => {
  it("says so when there are no rooms, and invents none", async () => {
    hostAnswers({ rooms: [], examples: [] });
    render(<Landing onOpen={() => {}} onJoin={() => {}} />);
    expect(await screen.findByText(/No open rooms here yet/)).toBeTruthy();
    expect(screen.queryByText(/sample/i)).toBeNull();
    expect(screen.queryAllByRole("button", { name: /seats?|closes/i })).toEqual([]);
  });

  it("treats a host that refuses as no rooms", async () => {
    hostAnswers({}, false);
    render(<Landing onOpen={() => {}} onJoin={() => {}} />);
    expect(await screen.findByText(/No open rooms here yet/)).toBeTruthy();
  });

  it("marks sample rooms as samples everywhere they appear", async () => {
    hostAnswers({ rooms: [room(), room({ id: "r2", goal: "Goal two" })], examples: [] });
    render(<Landing onOpen={() => {}} onJoin={() => {}} />);
    expect(await screen.findByText("2 sample rooms on the map")).toBeTruthy();
    const pin = screen.getByRole("button", { name: /Goal one.*sample/ });
    expect(pin.textContent).toMatch(/· sample/);
    await userEvent.click(pin);
    expect(screen.getByRole("status").textContent).toMatch(/sample room/);
  });

  it("opens with the typed sentence, and not with an empty one", async () => {
    hostAnswers({ rooms: [], examples: [] });
    const onOpen = vi.fn();
    render(<Landing onOpen={onOpen} onJoin={() => {}} />);
    const send = screen.getByRole("button", { name: "Set the goal" }) as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    await userEvent.type(screen.getByLabelText("What should get done?"), "  Do the thing  ");
    await userEvent.click(send);
    expect(onOpen).toHaveBeenCalledWith("Do the thing");
  });

  it("fills the box from an example the host gave", async () => {
    hostAnswers({ rooms: [], examples: ["An example goal"] });
    render(<Landing onOpen={() => {}} onJoin={() => {}} />);
    await userEvent.click(await screen.findByRole("button", { name: "An example goal" }));
    expect((screen.getByLabelText("What should get done?") as HTMLInputElement).value).toBe(
      "An example goal",
    );
  });

  it("joins from a pasted link and refuses what is not a code", async () => {
    hostAnswers({ rooms: [], examples: [] });
    const onJoin = vi.fn();
    render(<Landing onOpen={() => {}} onJoin={onJoin} />);
    const box = screen.getByLabelText("Invitation link or code");
    await userEvent.type(box, "B12-7KQ");
    await userEvent.click(screen.getByRole("button", { name: "Join" }));
    expect(onJoin).not.toHaveBeenCalled();
    expect(screen.getByRole("alert").textContent).toMatch(/room code or an invitation link/);
    await userEvent.clear(box);
    await userEvent.type(box, `http://127.0.0.1/join#${SECRET}`);
    await userEvent.click(screen.getByRole("button", { name: "Join" }));
    expect(onJoin).toHaveBeenCalledWith(SECRET);
  });

  it("takes a start code out of the address", async () => {
    hostAnswers({ rooms: [], examples: [] });
    history.replaceState(null, "", `/#start=${SECRET}`);
    render(<Landing onOpen={() => {}} onJoin={() => {}} />);
    await waitFor(() => expect(location.hash).toBe(""));
    expect(sessionStorage.getItem("ck.start")).toBe(SECRET);
  });

  it("switches theme from the page and remembers it", async () => {
    hostAnswers({ rooms: [], examples: [] });
    render(<Landing onOpen={() => {}} onJoin={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Use dark theme" }));
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(storedTheme()).toBe("dark");
    await userEvent.click(screen.getByRole("button", { name: "Use light theme" }));
    expect(document.documentElement.dataset.theme).toBe("light");
  });
});

describe("the first route", () => {
  it("shows the map first, carries the sentence to /open, and comes back", async () => {
    hostAnswers({}, false);
    render(<App />);
    expect(await screen.findByRole("heading", { level: 1, name: /What needs doing/ })).toBeTruthy();
    await userEvent.type(screen.getByLabelText("What should get done?"), "Do the thing");
    await userEvent.click(screen.getByRole("button", { name: "Set the goal" }));
    expect(location.pathname).toBe("/open");
    expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Do the thing");
    history.back();
    expect(await screen.findByRole("heading", { level: 1, name: /What needs doing/ })).toBeTruthy();
  });
});

describe("theme", () => {
  it("starts light whatever is missing, and restores a stored dark", () => {
    expect(storedTheme()).toBe("light");
    chooseTheme("dark");
    document.documentElement.dataset.theme = "light";
    applyStoredTheme();
    expect(document.documentElement.dataset.theme).toBe("dark");
  });
});

describe("rooms", () => {
  it("keeps every room inside the map, including one alone", () => {
    expect(spots([room()])[0]).toEqual({ x: 50, y: 50 });
    const placed = spots([room({ lat: 10, lon: 10 }), room({ lat: 20, lon: 30 })]);
    expect(placed[0]).toEqual({ x: 14, y: 84 });
    expect(placed[1]).toEqual({ x: 86, y: 16 });
  });
  it("reads a secret from a link or alone, and nothing else", () => {
    expect(invitationIn(`https://host/join#${SECRET}`)).toBe(SECRET);
    expect(invitationIn(` ${SECRET} `)).toBe(SECRET);
    expect(invitationIn("B12-7KQ")).toBeNull();
    expect(invitationIn("https://host/join")).toBeNull();
  });
});
