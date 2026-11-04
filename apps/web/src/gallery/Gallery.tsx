// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import "../styles/gallery.css";
import { IMPLEMENTED } from "../catalog";
import { Badge } from "../components/primitives";
import { Basic } from "./SectionsBasic";
import { Lens } from "./SectionsLens";
import { Shell } from "./SectionsShell";
import { Work } from "./SectionsWork";
import { SHEETS } from "./sheets";
import { TableGallery } from "./TableGallery";

type Theme = "light" | "dark";

function initialTheme(): Theme | null {
  const q = new URLSearchParams(location.search).get("theme");
  return q === "dark" || q === "light" ? q : null;
}

/** Every implemented component in every state the sheets show, with its name and props. */
export function Gallery() {
  const [theme, setTheme] = useState<Theme | null>(initialTheme);
  const where = location.pathname.split("/")[2] ?? "";
  const Sheet = SHEETS[where];
  useEffect(() => {
    const root = document.documentElement;
    if (theme) root.dataset.theme = theme;
    else delete root.dataset.theme;
  }, [theme]);
  if (where === "table") return <TableGallery />;
  return (
    <div className="sheet" data-testid="gallery" data-theme-choice={theme ?? "system"}>
      <div className="sheet-head">
        <div>
          <div className="eyebrow">coalitionkit/v0_9 · web renderer</div>
          <div className="sheet-title">Component gallery</div>
          <div className="sheet-sub">
            Every implemented component in every state. Neutral example data only.
          </div>
        </div>
        <div className="h-right gallery-bar">
          <Badge kind="example" label="Example data" />
          <span className="scope">{IMPLEMENTED.length} catalog components registered</span>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => setTheme("light")}
            aria-pressed={theme === "light"}
          >
            Light
          </button>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => setTheme("dark")}
            aria-pressed={theme === "dark"}
          >
            Dark
          </button>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={() => setTheme(null)}
            aria-pressed={theme === null}
          >
            System
          </button>
        </div>
      </div>
      {Sheet ? (
        <Sheet />
      ) : (
        <>
          <nav className="gallery-sheets" aria-label="Design sheets">
            {Object.keys(SHEETS).map((nn) => (
              <a key={nn} href={`/gallery/${nn}`}>
                Sheet {nn}
              </a>
            ))}
            <a href="/gallery/table">The Table</a>
          </nav>
          <Basic />
          <Work />
          <Shell />
          <Lens />
        </>
      )}
      <div className="small" style={{ marginTop: 18 }}>
        Every value bound by path; numbers carry provenance; nothing renders outside the viewer
        scope.
      </div>
    </div>
  );
}
