// SPDX-License-Identifier: Apache-2.0
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { VideoCall, VoiceCall } from "./calls";

afterEach(cleanup);

it("renders distinct person, screen and agent tiles and dispatches call controls", () => {
  const send = vi.fn();
  const { container } = render(
    <VideoCall
      p={{
        tiles: [
          { participant: "Member A", kind: "person" },
          { participant: "Member B", kind: "screen", label: "Shared view" },
          { participant: "Agent", kind: "agent" },
        ],
        captions: true,
      }}
      send={send}
    />,
  );
  expect(container.querySelectorAll(".f03-person")).toHaveLength(1);
  expect(screen.getByRole("img", { name: "Shared view" })).toBeVisible();
  for (const [name, event, data] of [
    ["Mute", "call.mute", { muted: true }],
    ["Camera", "call.camera", { enabled: true }],
    ["Captions", "call.captions", { enabled: false }],
  ] as const) {
    fireEvent.click(screen.getByRole("button", { name }));
    expect(send).toHaveBeenLastCalledWith(event, data);
  }
  fireEvent.click(screen.getByRole("button", { name: "Share" }));
  expect(send).toHaveBeenLastCalledWith("call.share");
  fireEvent.click(screen.getByRole("button", { name: "End call" }));
  expect(send).toHaveBeenLastCalledWith("call.end");
  expect(screen.getByRole("button", { name: "Mute" })).toBeDisabled();
});

it("toggles the voice speaker and disables controls after ending", () => {
  const send = vi.fn();
  render(<VoiceCall p={{ speaking: "Member A", participants: ["Member A"] }} send={send} />);
  fireEvent.click(screen.getByRole("button", { name: "Speaker" }));
  expect(send).toHaveBeenLastCalledWith("call.speaker", { enabled: true });
  fireEvent.click(screen.getByRole("button", { name: "End call" }));
  expect(screen.getByRole("button", { name: "Speaker" })).toBeDisabled();
});
