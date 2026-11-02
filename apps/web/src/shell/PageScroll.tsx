// SPDX-License-Identifier: Apache-2.0
// The page's scroll marker: a slim pill in the palette, in place of the system scrollbar.
// Wheel, touch and keys scroll the page as usual. The pill shows where you are and can be dragged.
import { type PointerEvent, useEffect, useRef, useState } from "react";
import "./page-scroll.css";

const MIN_THUMB = 40;
const LINGER_MS = 900;

type Thumb = { top: number; height: number };

export function thumbFor(view: number, content: number, scrolled: number): Thumb | null {
  if (content <= view + 1) return null;
  const height = Math.max(MIN_THUMB, (view * view) / content);
  const share = Math.min(1, Math.max(0, scrolled / (content - view)));
  return { top: share * (view - height), height };
}

export function PageScroll() {
  const [thumb, setThumb] = useState<Thumb | null>(null);
  const [moving, setMoving] = useState(false);
  const [dragging, setDragging] = useState(false);
  const grab = useRef<{ y: number; scrolled: number } | null>(null);

  useEffect(() => {
    const root = document.documentElement;
    const measure = () => setThumb(thumbFor(root.clientHeight, root.scrollHeight, root.scrollTop));
    let timer: ReturnType<typeof setTimeout> | undefined;
    const onScroll = () => {
      measure();
      setMoving(true);
      clearTimeout(timer);
      timer = setTimeout(() => setMoving(false), LINGER_MS);
    };
    measure();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", measure);
    // Pages change height without a scroll or a resize: routes, cards arriving.
    const watcher = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(measure);
    watcher?.observe(document.body);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", measure);
      watcher?.disconnect();
    };
  }, []);

  if (!thumb) return null;

  const onDown = (e: PointerEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.currentTarget.setPointerCapture?.(e.pointerId);
    grab.current = { y: e.clientY, scrolled: document.documentElement.scrollTop };
    setDragging(true);
  };
  const onMove = (e: PointerEvent<HTMLDivElement>) => {
    if (!grab.current) return;
    const root = document.documentElement;
    const room = root.clientHeight - thumb.height;
    const perPixel = (root.scrollHeight - root.clientHeight) / room;
    const top = grab.current.scrolled + (e.clientY - grab.current.y) * perPixel;
    window.scrollTo({ top, behavior: "instant" });
  };
  const onUp = () => {
    grab.current = null;
    setDragging(false);
  };

  return (
    <div className="page-scroll" data-live={moving || dragging ? "" : undefined} aria-hidden="true">
      <div
        className="page-scroll-thumb"
        style={{ height: thumb.height, transform: `translateY(${thumb.top}px)` }}
        onPointerDown={onDown}
        onPointerMove={onMove}
        onPointerUp={onUp}
        onPointerCancel={onUp}
      />
    </div>
  );
}
