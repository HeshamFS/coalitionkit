// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { Glyph } from "./Glyph";
import { Player } from "./Player";
import { number, rows, str, type ViewProps } from "./shared";

export function Media({ name, p, send }: ViewProps) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const src = str(p.src);
  // biome-ignore lint/correctness/useExhaustiveDependencies: a new host source starts a new image load
  useEffect(() => {
    setFailed(false);
    setLoaded(false);
  }, [src]);
  if (name === "Image")
    return (
      <figure className="f01-image" data-state={failed ? "failed" : loaded ? "loaded" : "loading"}>
        {failed ? (
          <span role="img" aria-label={str(p.alt)}>
            <svg className="ico" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M2 2l20 20M21 15V5H9M3 7v12h14" />
            </svg>
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
  return <Player name={name} p={p} send={send} />;
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
        <Glyph name="upload" size="lg" />
        <b>Drop to add to your vault</b>
        <span className="small">
          {accept
            ? accept
                .replace("application/pdf", "PDF")
                .replace("image/*", "images")
                .replace("text/csv", "CSV")
                .replaceAll(",", ", ")
            : "Choose files"}
          {p.maxBytes ? ` · up to ${number(p.maxBytes) / 1000000} MB` : ""}
        </span>
        <input
          className="sr-only"
          type="file"
          multiple
          accept={accept}
          onChange={(e) => add(e.target.files)}
        />
      </label>
      {rows(p.target).map((file) => (
        <div className="f01-file" key={str(file.id, str(file.name))}>
          <span className="f01-file-ext">{str(file.name).split(".").pop()?.toUpperCase()}</span>
          <div className="col grow" style={{ gap: file.progress !== undefined ? 3 : 0 }}>
            <span className="h-title">{str(file.name)}</span>
            {file.progress !== undefined ? (
              <div
                className="f01-bar"
                role="progressbar"
                aria-label={str(file.name)}
                aria-valuenow={number(file.progress)}
                aria-valuemin={0}
                aria-valuemax={100}
              >
                <span style={{ width: `${Math.min(100, Math.max(0, number(file.progress)))}%` }} />
              </div>
            ) : (
              <span className="small">{str(file.meta)}</span>
            )}
          </div>
          {file.progress !== undefined ? (
            <span className="st">{number(file.progress)} %</span>
          ) : (
            <span className="badge b-vault">Private</span>
          )}
        </div>
      ))}
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
