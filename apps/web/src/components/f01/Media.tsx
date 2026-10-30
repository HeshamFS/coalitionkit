// SPDX-License-Identifier: Apache-2.0
import { useState } from "react";
import { number, str, type ViewProps } from "./shared";

export function Media({ name, p, send }: ViewProps) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const src = str(p.src);
  if (name === "Image")
    return (
      <figure className="f01-image" data-state={failed ? "failed" : loaded ? "loaded" : "loading"}>
        {failed ? (
          <span role="img" aria-label={str(p.alt)}>
            Image unavailable
          </span>
        ) : src ? (
          <img
            src={src}
            alt={str(p.alt)}
            onLoad={() => setLoaded(true)}
            onError={() => setFailed(true)}
          />
        ) : (
          <span className="skel" role="img" aria-label={str(p.alt)} />
        )}
        {p.evidence ? (
          <figcaption className="small">Evidence · {str(p.evidence)}</figcaption>
        ) : null}
      </figure>
    );
  const events = {
    onPlay: () => send("media.play"),
    onPause: () => send("media.pause"),
    onSeeked: (e: React.SyntheticEvent<HTMLMediaElement>) =>
      send("media.seek", { t: e.currentTarget.currentTime }),
  };
  return name === "Video" ? (
    <video
      className="f01-video"
      controls
      src={src || undefined}
      poster={str(p.poster) || undefined}
      {...events}
    >
      <track kind="captions" src={str(p.captions) || undefined} label="Captions" default />
    </video>
  ) : (
    <div className="card">
      <span className="small">{str(p.title)}</span>
      <audio controls src={src || undefined} {...events}>
        <track kind="captions" />
      </audio>
    </div>
  );
}

export function FileDrop({ p, send }: ViewProps) {
  const [over, setOver] = useState(false);
  const [error, setError] = useState("");
  const [files, setFiles] = useState<string[]>([]);
  const accept = Array.isArray(p.accept) ? p.accept.map((x) => str(x)).join(",") : "";
  const add = (list: FileList | null) => {
    if (!list) return;
    for (const file of Array.from(list)) {
      if (p.maxBytes && file.size > number(p.maxBytes)) {
        setError(`${file.name} exceeds the size limit`);
        continue;
      }
      const types = accept.split(",").filter(Boolean);
      if (
        types.length &&
        !types.some((type) =>
          type.startsWith(".")
            ? file.name.endsWith(type)
            : type.endsWith("/*")
              ? file.type.startsWith(type.slice(0, -1))
              : file.type === type,
        )
      ) {
        setError(`${file.name} is not an accepted type`);
        continue;
      }
      setError("");
      setFiles((v) => [...v, file.name]);
      send("file.add", { file });
    }
  };
  return (
    <div>
      <label
        className={`f01-drop ${over ? "is-over" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          add(e.dataTransfer.files);
        }}
      >
        <b>Drop to add to your vault</b>
        <span className="small">
          {accept || "Choose files"}
          {p.maxBytes ? ` · up to ${number(p.maxBytes) / 1000000} MB` : ""}
        </span>
        <input type="file" multiple accept={accept} onChange={(e) => add(e.target.files)} />
      </label>
      {files.map((file) => (
        <div className="card" key={file}>
          {file}
          <span className="small">Waiting for host</span>
        </div>
      ))}
      {error && (
        <span className="f01-error" role="alert">
          {error}
        </span>
      )}
    </div>
  );
}
