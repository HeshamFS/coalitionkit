// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { DiarizedTranscript, NegotiationTheatre } from "./dialogue";
import { CallInvite } from "./invite";
import { CoalitionThread } from "./thread";

afterEach(cleanup);

it("opens an embedded thread card using its owning message id", () => {
  const send = vi.fn();
  render(
    <CoalitionThread
      p={{
        messages: [
          {
            id: "m1",
            author: { label: "Member", initial: "M", kind: "agent" },
            text: "Ready",
            card: { title: "Offer", action: "Add to my plan" },
          },
        ],
      }}
      send={send}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Add to my plan" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("message.open", { id: "m1" });
});

it("inspects the selected protocol turn without approving its proposal", () => {
  const send = vi.fn();
  render(
    <NegotiationTheatre
      p={{ events: [{ event_ref: "e1", type: "coalition.propose", text: "Plan", checked: false }] }}
      send={send}
    />,
  );
  expect(screen.queryByText("steward passed")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Inspect turn" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("turn.inspect", { event_ref: "e1" });
});

it("requests review of extracted items before posting", () => {
  const send = vi.fn();
  const item = { id: "n1", segment: "s1", kind: "need", text: "Need: Resource 1" };
  render(
    <DiarizedTranscript
      p={{ segments: [{ id: "s1", text: "Resource 1", start: "12:01" }], extracted: [item] }}
      send={send}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Need: Resource 1" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("extract.review", { id: "n1" });
});

it("keeps call consents off until the caller explicitly selects them", () => {
  const send = vi.fn();
  render(
    <CallInvite
      p={{
        title: "Sync",
        caller: "Member",
        consents: [
          { kind: "transcript", label: "Transcribe" },
          { kind: "auto-post", label: "Auto-post" },
        ],
      }}
      send={send}
    />,
  );
  expect(screen.getByRole("checkbox", { name: "Transcribe" })).not.toBeChecked();
  expect(screen.getByRole("checkbox", { name: "Auto-post" })).not.toBeChecked();
  fireEvent.click(screen.getByRole("checkbox", { name: "Transcribe" }));
  fireEvent.click(screen.getByRole("button", { name: "Join" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("call.join", { consents: { transcript: true } });
});
