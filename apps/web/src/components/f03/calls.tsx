// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { type Data, Frame, label, list, obj, text, type View } from "../f02/ui";
import "./calls.css";

function Icon({ name }: { name: string }) {
  const paths: Record<string, string> = {
    Mute: "M9 6a3 3 0 0 1 6 0v5a3 3 0 0 1-6 0z M5 11a7 7 0 0 0 14 0M12 18v3",
    Camera:
      "M4 6h10a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2z M16 10l6-3v10l-6-3",
    Share: "M5 4h14a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z M8 20h8M12 16v4",
    Captions: "M4 6h16M4 12h16M4 18h10",
    Speaker: "M11 5L6 9H2v6h4l5 4zM15.5 8.5a5 5 0 0 1 0 7",
    "End call": "M3 15c5-5 13-5 18 0l-2 3-4-1v-3a12 12 0 0 0-6 0v3l-4 1z",
  };
  return (
    <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
      <path d={paths[name]} />
    </svg>
  );
}

function Controls({
  send,
  voice,
  end,
  ended,
  captions,
}: {
  send: View["send"];
  voice?: boolean;
  end: () => void;
  ended: boolean;
  captions?: boolean;
}) {
  const [active, set] = useState<Record<string, boolean>>({ Captions: !!captions });
  const names = voice
    ? ["Mute", "Speaker", "End call"]
    : ["Mute", "Camera", "Share", "Captions", "End call"];
  return (
    <div className="f03-call-controls">
      {names.map((name) => (
        <button
          type="button"
          key={name}
          aria-label={name}
          disabled={ended}
          className={name === "End call" ? "f03-end-call" : ""}
          aria-pressed={name === "Share" || name === "End call" ? undefined : !!active[name]}
          onClick={() => {
            if (name === "End call") {
              end();
              send("call.end");
              return;
            }
            if (name === "Share") {
              send("call.share");
              return;
            }
            const enabled = !active[name];
            set({ ...active, [name]: enabled });
            send(`call.${name.toLowerCase()}`, name === "Mute" ? { muted: enabled } : { enabled });
          }}
        >
          <Icon name={name} />
        </button>
      ))}
    </div>
  );
}

function Tile({ tile, index }: { tile: Data; index: number }) {
  const participant =
    typeof tile.participant === "string" ? text(tile.participant) : label(obj(tile.participant));
  const kind = text(tile.kind) || "person";
  return (
    <div
      className={`f03-call-tile f03-call-${kind} ${tile.speaking ? "f03-call-speaking" : ""}`}
      data-seat={index % 2}
    >
      {kind === "person" ? (
        <svg className="f03-person" viewBox="0 0 100 60" aria-hidden="true">
          <circle cx="50" cy="26" r="11" />
          <path d="M28 60c3-14 12-20 22-20s19 6 22 20z" />
        </svg>
      ) : kind === "screen" ? (
        <svg
          className="f03-screen"
          viewBox="0 0 120 70"
          role="img"
          aria-label={text(tile.label) || "Shared screen preview"}
        >
          <rect x="6" y="6" width="108" height="58" rx="3" />
          <path d="M12 54 C30 50 40 20 60 22 S90 46 108 14" />
          <text x="12" y="16">
            {text(tile.label)}
          </text>
        </svg>
      ) : (
        <>
          <span className="av av-xl av-sq">{text(tile.initial) || participant.slice(0, 1)}</span>
          <div className="f03-call-wave" aria-hidden="true">
            {[6, 12, 16, 9, 14].map((height, i) => (
              <i key={String(i)} style={{ height }} />
            ))}
          </div>
        </>
      )}
      {kind === "agent" ? (
        <span className="f03-agent-caption">
          {participant} · {tile.speaking ? "speaking" : "listening, not speaking"}
        </span>
      ) : (
        <span className={`f03-call-tag ${kind === "screen" ? "s5" : index % 2 ? "s1" : "s3"}`}>
          {participant}
          {tile.speaking ? " · speaking" : kind === "screen" ? " · screen" : ""}
          {!!tile.muted && (
            <svg className="ico" viewBox="0 0 24 24" aria-label="Muted">
              <path d="M2 2l20 20M9 9v3a3 3 0 0 0 5 2M15 9.3V5a3 3 0 0 0-6 0" />
            </svg>
          )}
        </span>
      )}
    </div>
  );
}

export function VideoCall({ p, send }: View) {
  const [ended, end] = useState(false);
  return (
    <Frame name="VideoCall" state={ended ? "ended" : list(p.tiles).length ? "live" : "connecting"}>
      <div className="f03-video-heading">
        <i />
        <b>{ended ? "Call ended" : text(p.title) || "Coalition call"}</b>
        {!!p.elapsed && <span>· {text(p.elapsed)}</span>}
        <span className="f03-call-indicators">
          <span>{p.recording === "transcript" ? "REC transcript only" : "Recording off"}</span>
          {!!p.captions && <span>CC</span>}
        </span>
      </div>
      <div className="f03-video-grid">
        {list(p.tiles).map((tile, i) => (
          <Tile key={text(tile.id) || String(i)} tile={tile} index={i} />
        ))}
      </div>
      <Controls send={send} end={() => end(true)} ended={ended} captions={!!p.captions} />
    </Frame>
  );
}

export function VoiceCall({ p, send }: View) {
  const [ended, end] = useState(false);
  return (
    <Frame name="VoiceCall" state={ended ? "ended" : p.speaking ? "live" : "ringing"}>
      <div className="f03-phone-bar">
        <span>{text(p.clock)}</span>
        <span>5G</span>
      </div>
      <div className="f03-voice-body">
        <div className="f03-call-stack">
          {list(p.participants).map((person, i) => (
            <span
              key={label(person)}
              className={`av av-xl ${person.kind === "agent" ? "av-sq f03-voice-agent" : i % 2 ? "s1" : "s3"} ${label(person) === text(p.speaking) ? "f03-voice-speaking" : ""}`}
            >
              {text(person.initial) || label(person).slice(0, 1)}
            </span>
          ))}
        </div>
        <b>{ended ? "Call ended" : text(p.title) || "Coalition call"}</b>
        <span className="f03-voice-time">
          {p.elapsed ? `${text(p.elapsed)} · ` : ""}
          {text(p.speaking)} speaking
        </span>
        {!!p.caption && <div className="f03-voice-caption">{text(p.caption)}</div>}
      </div>
      <Controls voice send={send} end={() => end(true)} ended={ended} />
    </Frame>
  );
}
