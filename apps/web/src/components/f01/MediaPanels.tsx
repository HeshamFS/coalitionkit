// SPDX-License-Identifier: Apache-2.0
import { One } from "../../gallery/Drawn";

const preview = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 64"><defs><linearGradient id="g" x2=".3" y2="1"><stop stop-color="#3b4a63"/><stop offset="1" stop-color="#1b2436"/></linearGradient></defs><path fill="url(#g)" d="M0 0h100v64H0z"/><path fill="#56678a" d="M0 50 30 30 50 44 70 22 100 46v18H0z"/><circle cx="78" cy="14" r="6" fill="#a9c6fb"/></svg>')}`;
export function Images() {
  return (
    <>
      <div className="g3" style={{ gap: 6 }}>
        {[
          ["loading", ""],
          ["loaded", preview],
          ["failed", "data:image/png;base64,invalid"],
        ].map(([state, src]) => (
          <div className="col" key={state}>
            <One
              component="Image"
              props={{ alt: "Resource preview", src: { path: "/src" } }}
              data={{ src }}
            />
            <span className="st">{state}</span>
          </div>
        ))}
      </div>
      <div className="row small">
        <One component="Badge" props={{ kind: "measured", label: "Evidence" }} />
        Resource record photo, cropped by your agent
      </div>
    </>
  );
}
export function Files() {
  return (
    <One
      component="FileDrop"
      props={{
        accept: ["application/pdf", "image/*", "text/csv"],
        maxBytes: { value: 20000000, event_ref: "example" },
        target: { path: "/files" },
      }}
      data={{
        files: [
          {
            id: "f1",
            name: "resource-log-member-b.pdf",
            progress: { value: 72, event_ref: "example" },
          },
          { id: "f2", name: "resource-scan-01.csv", meta: "1.2 MB · stays in your vault" },
        ],
      }}
    />
  );
}

const bound = (value: number) => ({ value, event_ref: "example" });
export function VoiceNote() {
  return (
    <One
      component="AudioPlayer"
      props={{
        duration: bound(19),
        elapsed: bound(7),
        waveform: [8, 16, 22, 12, 18, 26, 14, 9, 20, 24, 12, 17, 8, 22, 14, 10, 19, 7, 15, 11].map(
          (n) => bound(n / 26),
        ),
        transcript: { path: "/transcript" },
      }}
      data={{ transcript: '"I can take the early task but not the later transfer…"' }}
    />
  );
}
const poster = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 150"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="#24324a"/><stop offset="1" stop-color="#0e1726"/></linearGradient></defs><path fill="url(#g)" d="M0 0h300v150H0z"/><rect x="110" y="40" width="80" height="60" rx="6" fill="#33445f"/><rect x="122" y="52" width="56" height="36" rx="3" fill="#e0703a" opacity=".85"/></svg>')}`;
export function VideoPanel() {
  return (
    <One
      component="Video"
      props={{
        duration: bound(37),
        elapsed: bound(14),
        poster: { path: "/poster" },
        caption: "Resource leaving the station at 1 150 units",
      }}
      data={{ poster }}
    />
  );
}
