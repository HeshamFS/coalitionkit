// SPDX-License-Identifier: Apache-2.0
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { Composer } from "./composer";

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});

it("inserts a mention at the end of existing text and sends the chosen scope", () => {
  const send = vi.fn();
  render(
    <Composer
      p={{ audience: "coalition", mentions: [{ label: "Member B", handle: "B" }] }}
      send={send}
    />,
  );
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "Can @" } });
  fireEvent.click(screen.getByRole("button", { name: /Member B/ }));
  expect(screen.getByRole("textbox")).toHaveValue("Can @B ");
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("message.send", {
    text: "Can @B ",
    scope: "coalition",
  });
});

it("publishes slash needs through their catalog event", () => {
  const send = vi.fn();
  render(<Composer p={{ audience: "coalition" }} send={send} />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "/need Resource 1" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("need.publish", {
    text: "Resource 1",
    scope: "coalition",
  });
});

it("does not send a private command to the coalition audience", () => {
  const send = vi.fn();
  render(<Composer p={{ audience: "coalition" }} send={send} />);
  fireEvent.change(screen.getByRole("textbox"), { target: { value: "/private A private note" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));
  expect(send).toHaveBeenCalledExactlyOnceWith("message.send", {
    text: "/private A private note",
    scope: "me",
  });
});

it("shows elapsed recording time and returns to the editor when stopped", () => {
  vi.useFakeTimers();
  const send = vi.fn();
  render(<Composer p={{}} send={send} />);
  fireEvent.click(screen.getByRole("button", { name: "Record" }));
  act(() => vi.advanceTimersByTime(6000));
  expect(screen.getByText("0:06")).toBeVisible();
  fireEvent.click(screen.getByRole("button", { name: "Stop" }));
  expect(screen.getByRole("textbox")).toBeVisible();
  expect(send).toHaveBeenNthCalledWith(1, "voice.record");
  expect(send).toHaveBeenNthCalledWith(2, "voice.record");
});
