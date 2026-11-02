// SPDX-License-Identifier: Apache-2.0
// The bar on every public page: the brand, the ways in, and the theme. The first screen, the room
// forming, the Door and joining all wear this one, so they read as one place.
import { type ReactNode, useRef, useState } from "react";
import { chooseTheme, storedTheme, type Theme } from "../shell/theme";
import { Logo } from "./marks";
import { QrScanner } from "./QrScanner";
import { invitationIn } from "./rooms";

function CodeBox({ onJoin }: { onJoin: (secret: string) => void }) {
  const [text, setText] = useState("");
  const [note, setNote] = useState("");
  return (
    <form
      className="ld-code"
      onSubmit={(e) => {
        e.preventDefault();
        const secret = invitationIn(text);
        if (secret) onJoin(secret);
        else setNote("That isn't a room code or an invitation link.");
      }}
    >
      <label htmlFor="ld-code" className="sr-only">
        Invitation link or code
      </label>
      <input
        id="ld-code"
        value={text}
        placeholder="Have a code?"
        autoComplete="off"
        spellCheck={false}
        onChange={(e) => {
          setText(e.target.value);
          setNote("");
        }}
      />
      <button type="submit" disabled={!text.trim()}>
        Join
      </button>
      {note && (
        <p className="ld-code-note" role="alert">
          {note}
        </p>
      )}
    </form>
  );
}

function ScanButton({ onJoin }: { onJoin: (secret: string) => void }) {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  return (
    <>
      <button
        ref={button}
        type="button"
        className="ld-scan"
        aria-label="Scan QR"
        onClick={() => setOpen(true)}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path d="M9 9h6v6H9z" fill="currentColor" />
        </svg>
        <span>Scan QR</span>
      </button>
      {open && (
        <QrScanner
          onJoin={(secret) => {
            setOpen(false);
            onJoin(secret);
          }}
          onClose={() => {
            setOpen(false);
            button.current?.focus();
          }}
        />
      )}
    </>
  );
}

function ThemeButton({ theme, onChange }: { theme: Theme; onChange: (t: Theme) => void }) {
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button
      type="button"
      className="ld-theme"
      aria-label={`Use ${next} theme`}
      onClick={() => onChange(next)}
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        {theme === "dark" ? (
          <>
            <circle cx="12" cy="12" r="4" stroke="currentColor" strokeWidth="2" />
            <path
              d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6 7 7M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </>
        ) : (
          <path
            d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
        )}
      </svg>
    </button>
  );
}

export function PublicNav({
  onJoin,
  onTheme,
  links,
  ways = true,
}: {
  onJoin: (secret: string) => void;
  onTheme?: (t: Theme) => void;
  links?: ReactNode;
  /** The code box and scanner: left out once someone is already holding a room's Door. */
  ways?: boolean;
}) {
  const [theme, setTheme] = useState<Theme>(() => storedTheme());
  return (
    <header className="ld-nav">
      <a className="ld-brand" href="/" aria-label="coalitionkit home">
        <Logo />
        <span>coalitionkit</span>
      </a>
      {links && (
        <nav className="ld-links" aria-label="Page">
          {links}
        </nav>
      )}
      <div className="ld-right">
        {ways && <CodeBox onJoin={onJoin} />}
        {ways && <ScanButton onJoin={onJoin} />}
        <ThemeButton
          theme={theme}
          onChange={(t) => {
            chooseTheme(t);
            setTheme(t);
            onTheme?.(t);
          }}
        />
      </div>
    </header>
  );
}
