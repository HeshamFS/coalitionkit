// SPDX-License-Identifier: Apache-2.0
import { act, fireEvent, render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PageScroll, thumbFor } from "./PageScroll";

function sizePage(view: number, content: number, scrolled = 0) {
  const root = document.documentElement;
  Object.defineProperty(root, "clientHeight", { configurable: true, value: view });
  Object.defineProperty(root, "scrollHeight", { configurable: true, value: content });
  Object.defineProperty(root, "scrollTop", { configurable: true, writable: true, value: scrolled });
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  sizePage(0, 0);
});

describe("thumbFor", () => {
  it("is absent when the page fits", () => {
    expect(thumbFor(800, 800, 0)).toBeNull();
  });
  it("sizes by the share of the page in view and travels the whole rail", () => {
    expect(thumbFor(800, 1600, 0)).toEqual({ top: 0, height: 400 });
    expect(thumbFor(800, 1600, 800)).toEqual({ top: 400, height: 400 });
  });
  it("stays big enough to grab on a very long page", () => {
    expect(thumbFor(800, 800000, 0)?.height).toBe(40);
  });
  it("stays on the rail when the page overscrolls", () => {
    expect(thumbFor(800, 1600, -50)?.top).toBe(0);
    expect(thumbFor(800, 1600, 900)?.top).toBe(400);
  });
});

describe("PageScroll", () => {
  it("draws nothing when the page fits", () => {
    sizePage(800, 800);
    const { container } = render(<PageScroll />);
    expect(container.querySelector(".page-scroll")).toBeNull();
  });

  it("shows while scrolling, then fades", () => {
    vi.useFakeTimers();
    sizePage(800, 1600);
    const { container } = render(<PageScroll />);
    const rail = container.querySelector(".page-scroll");
    expect(rail?.hasAttribute("data-live")).toBe(false);
    act(() => {
      fireEvent.scroll(window);
    });
    expect(rail?.hasAttribute("data-live")).toBe(true);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(rail?.hasAttribute("data-live")).toBe(false);
  });

  it("scrolls the page when dragged", () => {
    sizePage(800, 1600);
    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const { container } = render(<PageScroll />);
    const thumb = container.querySelector(".page-scroll-thumb") as HTMLElement;
    fireEvent.pointerDown(thumb, { clientY: 100 });
    fireEvent.pointerMove(thumb, { clientY: 200 });
    // The pill has 400 px of rail for 800 px of page, so 100 px of drag is 200 px of page.
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 200, behavior: "instant" });
    fireEvent.pointerUp(thumb);
    scrollTo.mockClear();
    fireEvent.pointerMove(thumb, { clientY: 300 });
    expect(scrollTo).not.toHaveBeenCalled();
  });
});
