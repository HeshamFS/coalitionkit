// SPDX-License-Identifier: Apache-2.0
import { fireEvent, render, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { expect, it, vi } from "vitest";
import { roomFixture } from "./fixture";
import { GermStepProvider } from "./germ";
import { Decisions, MeasuredStrip, Participants, Plans, Privacy, Schedule, Wiring } from "./parts";
import { initialsOf, pillFor } from "./status";

const Now = ({ children }: { children: ReactNode }) => (
  <GermStepProvider value={0}>{children}</GermStepProvider>
);
const base = { ready: true };

it("renders one card per member from the feed state, in join order and seat colour", async () => {
  render(
    <Now>
      <Participants state={roomFixture} {...base} />
    </Now>,
  );
  const cards = await screen.findAllByRole("article");
  expect(cards).toHaveLength(2);
  expect(within(cards[0] as HTMLElement).getByText("Member A")).toBeInTheDocument();
  expect(within(cards[0] as HTMLElement).getByText("Agent A on Vendor A")).toBeInTheDocument();
  expect(within(cards[0] as HTMLElement).getByText("Review item")).toBeInTheDocument();
  expect(within(cards[1] as HTMLElement).getByText("Member 2")).toBeInTheDocument();
  const avatar = (card: HTMLElement) => card.querySelector<HTMLElement>(".room-avatar");
  expect(avatar(cards[0] as HTMLElement)?.style.background).toBe("var(--seat-1)");
  expect(avatar(cards[1] as HTMLElement)?.style.background).toBe("var(--seat-2)");
});

it("shows a skeleton with the catalog name until the data has arrived", () => {
  render(
    <Now>
      <Participants state={null} ready={false} />
    </Now>,
  );
  expect(screen.getByText("ParticipantCard")).toBeInTheDocument();
});

it("maps state words to the design system pills", () => {
  const own = { own: true, hasItem: true };
  const other = { own: false, hasItem: true };
  expect(pillFor("Agreed", other)).toEqual({ tone: "agreed", word: "Agreed" });
  expect(pillFor("Changed · ripple", other)).toEqual({ tone: "changed", word: "Changed" });
  expect(pillFor("Needs their yes", own)).toEqual({ tone: "needs", word: "Needs you" });
  expect(pillFor("Needs their yes", other)?.word).toBe("Needs their yes");
  expect(pillFor("Blocked · policy", other)).toEqual({ tone: "blocked", word: "Blocked" });
  expect(pillFor("", { own: false, hasItem: false })).toEqual({ tone: "private", word: "Private" });
  expect(pillFor("", other)).toBeNull();
  expect(initialsOf("Member 2")).toBe("M2");
});

it("shows the pill word on a card and a designed empty line when nothing is shared", async () => {
  render(
    <Now>
      <Participants state={roomFixture} {...base} />
    </Now>,
  );
  const cards = await screen.findAllByRole("article");
  expect(within(cards[1] as HTMLElement).getByText("Private")).toHaveClass("t-private");
  expect(screen.getByText("Nothing shared with you yet")).toBeInTheDocument();
  expect(screen.queryByText(/No current item in your projection/)).not.toBeInTheDocument();
});

const request = {
  id: "r1",
  kind: "plan",
  subjectId: "plan-1",
  revision: 1,
  message: "Review this",
};

it("renders the other panels from the projection and routes requests to trusted UI", async () => {
  const open = vi.fn();
  render(
    <Now>
      <Plans state={roomFixture} {...base} requests={[request]} onOpen={open} />
      <MeasuredStrip state={roomFixture} {...base} />
      <Wiring state={roomFixture} {...base} />
      <Decisions state={roomFixture} {...base} requests={[request]} onOpen={open} />
      <Privacy state={roomFixture} {...base} />
      <Schedule state={roomFixture} {...base} />
    </Now>,
  );
  for (const name of [
    "Plan options",
    "Measured",
    "Wiring · live",
    "Decisions",
    "What stayed private",
    "Timeline",
  ])
    expect(await screen.findByLabelText(name)).toBeInTheDocument();
  expect(screen.getByText("A · Option A")).toBeInTheDocument();
  expect(screen.getByText("Private notes")).toBeInTheDocument();
  expect(screen.getByText(/spent 0.04 EUR/)).toBeInTheDocument();
  expect(screen.queryByText(/\[MEASURED\]|calendars shared|time to first commitment/)).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Review plan A" }));
  expect(open).toHaveBeenCalledWith("r1");
});

it("shows designed empty states, never an invented value", async () => {
  render(
    <Now>
      <Participants state={{}} {...base} />
      <Plans state={{}} {...base} />
      <Wiring state={{}} {...base} />
      <Decisions state={{}} {...base} requests={[]} onOpen={() => {}} />
      <Privacy state={{}} {...base} />
      <Schedule state={{}} {...base} />
    </Now>,
  );
  for (const title of [
    "No participants yet",
    "No plans yet",
    "No events yet",
    "No decisions yet",
    "Nothing shared yet",
    "Nothing scheduled yet",
  ])
    expect(await screen.findByText(title)).toBeInTheDocument();
});
