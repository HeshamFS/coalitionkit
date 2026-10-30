// SPDX-License-Identifier: Apache-2.0
import { useEffect, useRef, useState } from "react";
import { number, str, type ViewProps } from "./shared";

const time = (seconds: number) =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;

export function Player({ name, p, send }: Pick<ViewProps, "name" | "p" | "send">) {
  const { ref, elapsed, duration, playing, error, src, events, seek, toggle } = usePlayback(
    p,
    send,
  );
  const [captions, setCaptions] = useState(true);
  const video = name === "Video";
  const waveform = Array.isArray(p.waveform) ? p.waveform : [];
  return (
    <div className={video ? "f01-video-player" : "card f01-audio-player"}>
      {video ? (
        <video
          ref={ref as React.RefObject<HTMLVideoElement>}
          src={src || undefined}
          poster={str(p.poster) || undefined}
          {...events}
        >
          <track kind="captions" src={str(p.captions) || undefined} label="Captions" default />
        </video>
      ) : (
        <audio ref={ref as React.RefObject<HTMLAudioElement>} src={src || undefined} {...events}>
          <track kind="captions" />
        </audio>
      )}
      {!video && p.title ? <span className="small">{str(p.title)}</span> : null}
      {video && captions && p.caption ? (
        <div className="f01-video-caption">
          <span>{str(p.caption)}</span>
        </div>
      ) : null}
      <div className="f01-player-controls">
        <button
          type="button"
          className="icon-btn f01-play"
          aria-label={playing ? "Pause" : "Play"}
          onClick={toggle}
        >
          <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
            {playing ? <path d="M7 5h4v14H7zM14 5h4v14h-4z" /> : <path d="M8 5l11 7-11 7z" />}
          </svg>
        </button>
        <div className={`f01-seek${waveform.length ? " f01-wave" : ""}`}>
          {waveform.length ? (
            waveform.map((sample, i) => (
              <i
                // biome-ignore lint/suspicious/noArrayIndexKey: fixed time bins in a waveform
                key={`sample-${i + 1}`}
                style={{
                  height: `${Math.max(2, Math.min(26, number(sample) * 26))}px`,
                  background:
                    i / waveform.length <= elapsed / Math.max(1, duration)
                      ? "var(--blue)"
                      : "var(--line-strong)",
                }}
              />
            ))
          ) : (
            <span
              className="f01-played"
              style={{ width: `${(elapsed / Math.max(1, duration)) * 100}%` }}
            />
          )}
          <input
            type="range"
            aria-label="Playback position"
            aria-valuetext={time(elapsed)}
            min={0}
            max={duration || 1}
            step={0.1}
            value={elapsed}
            onChange={(e) => seek(Number(e.target.value))}
          />
        </div>
        <span className="st">
          {time(elapsed)} / {time(duration)}
        </span>
        {video && (
          <button
            type="button"
            className="f01-cc"
            aria-label="Captions"
            aria-pressed={captions}
            onClick={() => {
              setCaptions(!captions);
              const track = ref.current?.textTracks[0];
              if (track) track.mode = captions ? "disabled" : "showing";
            }}
          >
            CC
          </button>
        )}
      </div>
      {!video && p.transcript ? (
        <div className="small f01-transcript">
          {str(p.transcript)} <span>transcript</span>
        </div>
      ) : null}
      {error && (
        <span role="status" className="small">
          {error}
        </span>
      )}
    </div>
  );
}

function usePlayback(p: ViewProps["p"], send: ViewProps["send"]) {
  const ref = useRef<HTMLMediaElement>(null);
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(number(p.elapsed));
  const [duration, setDuration] = useState(number(p.duration));
  const [error, setError] = useState("");
  const src = str(p.src);
  useEffect(() => {
    setElapsed(number(p.elapsed));
    if (ref.current && Number.isFinite(ref.current.duration))
      ref.current.currentTime = number(p.elapsed);
  }, [p.elapsed]);
  useEffect(() => setDuration(number(p.duration)), [p.duration]);
  // biome-ignore lint/correctness/useExhaustiveDependencies: reset playback when the host replaces the source
  useEffect(() => {
    setPlaying(false);
    setError("");
  }, [src]);
  const seek = (next: number) => {
    const value = Math.min(duration, Math.max(0, next));
    setElapsed(value);
    if (ref.current && src) ref.current.currentTime = value;
    else send("media.seek", { t: value });
  };
  const toggle = async () => {
    if (!ref.current || !src) {
      send(playing ? "media.pause" : "media.play");
      return;
    }
    if (playing) ref.current.pause();
    else {
      try {
        await ref.current.play();
        setError("");
      } catch {
        setError("Playback unavailable");
      }
    }
  };
  const events = {
    onPlay: () => {
      setPlaying(true);
      send("media.play");
    },
    onPause: () => {
      setPlaying(false);
      send("media.pause");
    },
    onEnded: () => setPlaying(false),
    onTimeUpdate: () => setElapsed(ref.current?.currentTime ?? 0),
    onLoadedMetadata: () => {
      const media = ref.current;
      if (media && Number.isFinite(media.duration)) {
        setDuration(media.duration);
        media.currentTime = Math.min(media.duration, number(p.elapsed));
      }
    },
    onSeeked: () => send("media.seek", { t: ref.current?.currentTime ?? elapsed }),
  };
  return { ref, elapsed, duration, playing, error, src, events, seek, toggle };
}
