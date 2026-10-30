// SPDX-License-Identifier: Apache-2.0
import { Action, type Props, rows, type Send, Table, usePreviewState } from "../f08/shared";
import "../../styles/f11.css";

export function ExportControl({ p, send }: { p: Props; send: Send }) {
  const preview = usePreviewState();
  if (preview === "wiped") return <span className="small">Vault wiped</span>;
  if (preview === "exporting") return <span role="status">Preparing your export…</span>;
  return (
    <>
      <Table data={p.items} columns={["kind", "size", "included"]} />
      <div className="row">
        <Action
          label="Download ZIP"
          event="export.zip"
          send={send}
          data={{ items: rows(p.items).filter((i) => i.included) }}
          primary
        />
        <Action label="Wipe vault" event="vault.wipe" send={send} />
      </div>
      <span className="st">Your signed log can still be verified after export.</span>
    </>
  );
}
