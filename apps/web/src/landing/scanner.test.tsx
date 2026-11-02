// SPDX-License-Identifier: Apache-2.0
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Landing } from "./Landing";
import { QrScanner } from "./QrScanner";
import { scannedInvitation } from "./rooms";

const SECRET = "abcdefghijklmnop1234";
const read = vi.hoisted(() => vi.fn());
vi.mock("jsqr", () => ({ default: read }));

const track = { stop: vi.fn() };

function camera(answer: () => Promise<unknown>) {
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia: vi.fn(answer) },
  });
}

beforeEach(() => {
  read.mockReset();
  track.stop.mockReset();
  camera(async () => ({ getTracks: () => [track] }));
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue(undefined);
  vi.spyOn(HTMLVideoElement.prototype, "videoWidth", "get").mockReturnValue(640);
  vi.spyOn(HTMLVideoElement.prototype, "videoHeight", "get").mockReturnValue(480);
  vi.spyOn(HTMLMediaElement.prototype, "readyState", "get").mockReturnValue(4);
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue({
    drawImage: () => {},
    getImageData: () => ({ data: new Uint8ClampedArray(4) }),
  } as unknown as RenderingContext);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  Reflect.deleteProperty(navigator, "mediaDevices");
});

describe("reading a scanned QR", () => {
  const here = "https://host.example";
  it("takes an invitation for this address", () => {
    expect(scannedInvitation(`${here}/join#${SECRET}`, here)).toEqual({ secret: SECRET });
    expect(scannedInvitation(SECRET, here)).toEqual({ secret: SECRET });
  });
  it("refuses another address and anything else", () => {
    expect(scannedInvitation(`https://other.example/join#${SECRET}`, here)).toEqual({
      problem: "elsewhere",
    });
    expect(scannedInvitation("javascript:alert(1)", here)).toEqual({ problem: "elsewhere" });
    expect(scannedInvitation("hello", here)).toEqual({ problem: "not-invitation" });
    expect(scannedInvitation(`${here}/join`, here)).toEqual({ problem: "not-invitation" });
  });
});

describe("the scanner", () => {
  it("is on the first screen, and joins with what it reads", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, json: async () => ({}) })),
    );
    read.mockReturnValue({ data: `${location.origin}/join#${SECRET}` });
    const onJoin = vi.fn();
    render(<Landing onOpen={() => {}} onJoin={onJoin} />);
    await userEvent.click(screen.getByRole("button", { name: "Scan QR" }));
    expect(screen.getByRole("dialog", { name: "Scan a room's QR" })).toBeTruthy();
    await waitFor(() => expect(onJoin).toHaveBeenCalledWith(SECRET));
    expect(track.stop).toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
    vi.unstubAllGlobals();
  });

  it("keeps looking after a QR that isn't an invitation, and says so", async () => {
    read.mockReturnValue({ data: "https://other.example/join#abcdefghijklmnop1234" });
    const onJoin = vi.fn();
    render(<QrScanner onJoin={onJoin} onClose={() => {}} />);
    expect(await screen.findByText(/another address/)).toBeTruthy();
    expect(onJoin).not.toHaveBeenCalled();
    expect(track.stop).not.toHaveBeenCalled();
  });

  it("stops the camera when closed", async () => {
    read.mockReturnValue(null);
    const onClose = vi.fn();
    const view = render(<QrScanner onJoin={() => {}} onClose={onClose} />);
    await waitFor(() => expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled());
    await act(async () => {});
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalled();
    view.unmount();
    expect(track.stop).toHaveBeenCalled();
  });

  it.each([
    ["NotAllowedError", /Camera access is off/],
    ["NotFoundError", /No camera found/],
    ["AbortError", /didn't start/],
  ])("explains %s and points to the code", async (name, text) => {
    camera(async () => {
      throw new DOMException("no", name);
    });
    render(<QrScanner onJoin={() => {}} onClose={() => {}} />);
    expect(await screen.findByText(text)).toBeTruthy();
    expect(screen.queryByLabelText("Camera view")).toBeNull();
    expect(screen.getByRole("button", { name: "Back" })).toBeTruthy();
  });

  it("says so on an address that has no camera access", async () => {
    Reflect.deleteProperty(navigator, "mediaDevices");
    render(<QrScanner onJoin={() => {}} onClose={() => {}} />);
    expect(await screen.findByText(/phone's camera app/)).toBeTruthy();
  });
});
