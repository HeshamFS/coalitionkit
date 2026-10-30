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
