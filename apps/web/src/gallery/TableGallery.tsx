// SPDX-License-Identifier: Apache-2.0
// The Table in the gallery: the real screen, driven by a scripted `Room` that steps through every
// phase, with local stand-ins for the host. It exists to be looked at; it is not the live path.
import { useEffect, useMemo, useState } from "react";
import { usePhoneRoom } from "../room/media";
import type { Call } from "../table/fixtureIo";
import { mockIo } from "../table/fixtureIo";
import type { Scene } from "../table/fixtures";
import type { Room } from "../table/room";
import { SCENES } from "../table/scenes";
import { TableView } from "../table/TableView";
import "./tableGallery.css";

const startAt = () => {
  const q = new URLSearchParams(location.search).get("scene");
  const at = SCENES.findIndex((s) => s.id === q);
  return Math.max(0, at);
};

export function TableGallery() {
  const [at, setAt] = useState(startAt);
  const [gone, setGone] = useState<string[]>([]);
  const [answered, setAnswered] = useState<string[]>([]);
  const [done, setDone] = useState<string[]>([]);
  const [focus, setFocus] = useState<string | null>(null);
  const [play, setPlay] = useState(() => new URLSearchParams(location.search).has("play"));
  const [calls] = useState<Call[]>([]);
  const phone = usePhoneRoom();
  const scene = SCENES[at] ?? (SCENES[0] as Scene);

  const go = (i: number) => {
    setAt(i);
    setGone([]);
    setAnswered([]);
    setDone([]);
    setFocus(null);
  };
  // biome-ignore lint/correctness/useExhaustiveDependencies: `go` only sets state
  useEffect(() => {
    if (!play) return;
    const t = setTimeout(() => go((at + 1) % SCENES.length), 5200);
    return () => clearTimeout(t);
  }, [play, at]);

  const io = useMemo(() => {
    const base = mockIo(calls);
    return {
      ...base,
      brief: async (id: string, a: Parameters<typeof base.brief>[1]) => {
        setAnswered((x) => [...x, id]);
        return base.brief(id, a);
      },
      done: async (id: string) => {
        setDone((x) => [...x, id]);
        return base.done(id);
      },
    };
  }, [calls]);

  const room: Room = {
    ...scene.room,
    mine: {
      ...scene.room.mine,
      brief: scene.room.mine.brief.map((b) =>
        answered.includes(b.id) ? { ...b, status: "answered" as const } : b,
      ),
      tasks: scene.room.mine.tasks.map((t) =>
        done.includes(t.task_id) ? { ...t, status: "done", can_mark_done: false } : t,
      ),
    },
  };
  return (
    <>
      <nav className="tbg-bar" aria-label="Scripted scenes">
        <b>The Table · scripted room, neutral words</b>
        {SCENES.map((s, i) => (
          <button key={s.id} type="button" aria-pressed={i === at} onClick={() => go(i)}>
            {s.name}
          </button>
        ))}
        <button type="button" aria-pressed={play} onClick={() => setPlay(!play)}>
          {play ? "Pause" : "Play"}
        </button>
      </nav>
      <TableView
        room={room}
        state={scene.state}
        requests={scene.requests.filter((r) => !gone.includes(r.id))}
        focus={focus}
        setFocus={setFocus}
        answer={async (a) => {
          await new Promise((r) => setTimeout(r, 120));
          setGone((x) => [...x, a.interrupt_id]);
          return { seq: 99, signature: "fixturesignaturevalue" };
        }}
        io={io}
        phone={phone}
        owner
        status="live"
      />
    </>
  );
}
