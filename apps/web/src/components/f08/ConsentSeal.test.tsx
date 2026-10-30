// SPDX-License-Identifier: Apache-2.0
import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { TrustedRequest } from "../../TrustedRequest";
import { CONSENT_HOLD_MS } from "./ConsentSeal";

const request = {
  id: "plan:p1:2:u1",
  kind: "plan",
  subjectId: "p1",
  revision: 2,
  message: "Approve Plan A?",
};
function mount(onAnswer = vi.fn()) {
  vi.useFakeTimers();
  vi.stubGlobal("matchMedia", () => ({
    matches: true,
    addEventListener() {},
    removeEventListener() {},
  }));
  const view = render(<TrustedRequest request={request} state={null} onAnswer={onAnswer} />);
  return {
    ...view,
    onAnswer,
    hold: screen.getByRole("button", { name: "Press and hold to approve" }),
  };
}
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});
it("posts one revision-bound answer after a full hold and waits for host acknowledgement", async () => {
  const { hold, onAnswer } = mount();
  fireEvent.pointerDown(hold, { button: 0 });
  await act(async () => vi.advanceTimersByTime(CONSENT_HOLD_MS));
  fireEvent.pointerUp(hold);
  fireEvent.click(hold);
  expect(onAnswer).toHaveBeenCalledExactlyOnceWith({ interrupt_id: request.id, consent: true });
  expect(screen.queryByText("Signed.")).not.toBeInTheDocument();
});
it("releasing early, cancelling, blurring, and unmounting cancel the hold", () => {
  const { hold, onAnswer, unmount } = mount();
  for (const cancel of [
    fireEvent.pointerUp,
    fireEvent.pointerCancel,
    fireEvent.blur,
    fireEvent.pointerLeave,
  ]) {
    fireEvent.pointerDown(hold, { button: 0 });
    act(() => vi.advanceTimersByTime(500));
    cancel(hold);
    act(() => vi.advanceTimersByTime(CONSENT_HOLD_MS));
  }
  fireEvent.pointerDown(hold, { button: 0 });
  unmount();
  act(() => vi.advanceTimersByTime(CONSENT_HOLD_MS));
  expect(onAnswer).not.toHaveBeenCalled();
});
it("offers a confirm step and shows only the acknowledged sequence and signature", async () => {
  const onAnswer = vi.fn().mockResolvedValue({ seq: 219, signature: "7c1e1234a0" });
  mount(onAnswer);
  fireEvent.click(screen.getByRole("button", { name: "Review and approve" }));
  expect(onAnswer).not.toHaveBeenCalled();
  await act(async () => fireEvent.click(screen.getByRole("button", { name: "Confirm approval" })));
  expect(onAnswer).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Signed.")).toBeInTheDocument();
  expect(screen.getByText("consent · seq 219 · sig 7c1e…a0")).toBeInTheDocument();
});
