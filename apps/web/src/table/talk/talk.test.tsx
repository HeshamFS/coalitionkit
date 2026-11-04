// SPDX-License-Identifier: Apache-2.0
import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { mockIo } from "../fixtureIo";
import { SCENES } from "../scenes";
import { TableView } from "../TableView";
import { latestBySeat, readTalk, type Talk } from "./talk";

const RAW = {
  open: true,
  round: 2,
  rounds: 2,
  stage: "start",
  waiting_for: [],
  thread: [
    {
      seq: 40,
      id: "e1",
      from: "p1",
      to: "room",
      intent: "trade",
      text: "I take the venue if someone keeps the books.",
      re: null,
      stage: "start",
    },
    {
      seq: 41,
      id: "e2",
      from: "p2",
      to: "p1",
      intent: "agree",
      text: "Deal, I keep the books.",
      re: "e1",
      stage: "start",
    },
    { seq: 42, id: "", from: "p3", to: "room", intent: "ask", text: "dropped: no id" },
  ],
  revised: [{ seat: "p2", needs: ["n3"], at: "2026-11-04T20:00:00Z" }],
  mine: { whisper: "I can only do mornings", listening: true },
};

describe("room.talk", () => {
  it("reads the talk and drops what is malformed", () => {
    const talk = readTalk(RAW);
    expect(talk.thread.map((t) => t.id)).toEqual(["e1", "e2"]);
    expect(talk.thread[1]).toMatchObject({ to: "p1", re: "e1", intent: "agree" });
    expect(readTalk("nonsense").thread).toEqual([]);
    expect(readTalk({ thread: [{ id: "x", text: "hi", intent: "shout" }] }).thread[0]?.intent).toBe(
      "caveat",
    );
    expect(latestBySeat(talk).map((t) => t.from)).toEqual(["p1", "p2"]);
  });

  it("shows the thread, the beams and the bubbles on the table", () => {
    const scene = SCENES.find((s) => s.id === "work");
    if (!scene) throw new Error("work scene");
    const talk: Talk = readTalk(RAW);
    const { container } = render(
      <TableView
        room={{ ...scene.room, talk }}
        state={scene.state}
        requests={scene.requests}
        focus={null}
        setFocus={() => {}}
        answer={async () => undefined}
        outcome={async () => ({ ok: true }) as never}
        io={mockIo([])}
        phone={false}
        owner={false}
        status="live"
      />,
    );
    const thread = screen.getByRole("region", { name: "What the agents said" });
    expect(within(thread).getByText(/round 2 of 2/)).toBeTruthy();
    expect(within(thread).getByText(/To everyone: I take the venue/)).toBeTruthy();
    expect(within(thread).getByText(/Deal, I keep the books/)).toBeTruthy();
    expect(within(thread).getByText(/changed its offer on/)).toBeTruthy();
    expect(within(thread).getByText("I can only do mornings")).toBeTruthy();
    expect(container.querySelectorAll(".tk-beam").length).toBe(2);
    expect(container.querySelector('.tk-beam[data-newest="true"][data-room="false"]')).toBeTruthy();
    expect(container.querySelectorAll(".tk-bubble").length).toBe(2);
  });

  it("draws nothing when nobody has spoken", () => {
    const scene = SCENES.find((s) => s.id === "work");
    if (!scene) throw new Error("work scene");
    const { container } = render(
      <TableView
        room={scene.room}
        state={scene.state}
        requests={scene.requests}
        focus={null}
        setFocus={() => {}}
        answer={async () => undefined}
        outcome={async () => ({ ok: true }) as never}
        io={mockIo([])}
        phone={true}
        owner={false}
        status="live"
      />,
    );
    expect(container.querySelector(".tk-thread")).toBeNull();
    expect(container.querySelector(".tk-bubble")).toBeNull();
  });
});
