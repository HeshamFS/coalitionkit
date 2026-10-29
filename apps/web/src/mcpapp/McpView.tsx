// SPDX-License-Identifier: Apache-2.0
import { A2uiSurface } from "@a2ui/react/v0_9";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Banner, Skeleton } from "../components/feedback";
import { fixedFields } from "../feed/derive";
import { SurfaceBook, type SurfaceEntry } from "../feed/surfaces";
import { type Bridge, resultText, type ToolResult } from "./bridge";
import {
  decisionCall,
  type McpData,
  type McpSummary,
  messagesFor,
  parseData,
  pickerParts,
  SURFACE_ID,
  surfaceParts,
  viewerStateOf,
} from "./surface";

/** How often the view asks the host for the current surface. A view cannot be pushed to. */
export const POLL_MS = 400;

type Notice = { tone: "agreed" | "blocked" | "info"; title: string };

/**
 * The surface of one participant inside an MCP host. It draws a tool result with the same
 * catalog the room uses, refreshes by calling `my_view` through the bridge, and answers a
 * decision only by calling the tool whose elicitation the server owns.
 */
export function McpView({ bridge, pollMs = POLL_MS }: { bridge: Bridge; pollMs?: number }) {
  const [coalition, setCoalition] = useState<string | null>(null);
  const [data, setData] = useState<McpData | null>(null);
  const [list, setList] = useState<McpSummary[] | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [entries, setEntries] = useState<SurfaceEntry[]>([]);
  const lastJson = useRef("");
  const current = useRef<string | null>(null);
  current.current = coalition;

  const accept = useCallback((d: McpData | null) => {
    if (!d) return;
    const json = JSON.stringify(d);
    if (d.surface) {
      if (d.coalition_id) setCoalition(d.coalition_id);
      if (json !== lastJson.current) {
        lastJson.current = json;
        setData(d);
        setList(null);
        setNotice(null);
      }
    } else if (d.coalitions) {
      if (d.coalitions.length === 1 && d.coalitions[0]?.coalition_id) {
        setCoalition(d.coalitions[0].coalition_id);
      } else if (json !== lastJson.current) {
        lastJson.current = json;
        setList(d.coalitions);
        setData(null);
      }
    } else if (d.coalition_id) {
      setCoalition(d.coalition_id);
    }
  }, []);

  const book = useMemo(
    () =>
      new SurfaceBook((action) => {
        const ctx = (action.context ?? {}) as Record<string, string>;
        if (action.name === "open" && ctx.coalition_id) {
          setCoalition(ctx.coalition_id);
          return;
        }
        if (action.name !== "decide" || !current.current) return;
        const call = decisionCall(current.current, ctx);
        if (!call) return;
        setNotice({ tone: "info", title: "Waiting for your answer in the host." });
        bridge
          .callTool(call.name, call.arguments)
          .then((r) =>
            setNotice({
              tone: r.isError ? "blocked" : "agreed",
              title: resultText(r) || (r.isError ? "The host refused." : "Done."),
            }),
          )
          .catch(() => setNotice({ tone: "blocked", title: "The host did not answer." }));
      }),
    [bridge],
  );

  useEffect(() => {
    const stop = book.subscribe(() => setEntries(book.list()));
    return () => {
      stop();
      book.dispose();
    };
  }, [book]);

  useEffect(() => {
    bridge.onTheme((t) => {
      document.documentElement.dataset.theme = t;
    });
    bridge.onToolResult((r: ToolResult) => {
      if (r.isError) {
        setNotice({ tone: "blocked", title: resultText(r) || "The host refused." });
        return;
      }
      accept(parseData(r.structuredContent));
    });
  }, [bridge, accept]);

  // Poll while the view is visible. One request at a time.
  useEffect(() => {
    if (!coalition) return;
    let busy = false;
    let stopped = false;
    const tick = async () => {
      if (busy || stopped || document.visibilityState === "hidden") return;
      busy = true;
      try {
        const r = await bridge.callTool("my_view", { coalition_id: coalition, device: "mcp-app" });
        if (stopped) return;
        if (r.isError) setNotice({ tone: "blocked", title: resultText(r) || "The host refused." });
        else accept(parseData(r.structuredContent));
      } catch {
        // The next tick tries again.
      } finally {
        busy = false;
      }
    };
    void tick();
    const timer = setInterval(() => void tick(), pollMs);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [bridge, coalition, pollMs, accept]);

  // Draw the current data. The surface is created once, then updated in place.
  useEffect(() => {
    const parts = list ? pickerParts(list) : data ? surfaceParts(data) : null;
    if (!parts) return;
    const first = book.list().length === 0;
    if (data) book.setFallbackFields(fixedFields(viewerStateOf(data)));
    book.apply(SURFACE_ID, messagesFor(parts, first));
  }, [book, data, list]);

  return (
    <main className="surface-host mcp-view" data-testid="mcp-view" data-coalition={coalition ?? ""}>
      {notice && <Banner tone={notice.tone} title={notice.title} />}
      {entries.length > 0 ? (
        entries.map((s) => <A2uiSurface key={s.id} surface={s.model} />)
      ) : (
        <Skeleton shape="card" label="Loading your view" />
      )}
    </main>
  );
}
