// SPDX-License-Identifier: Apache-2.0
// Minted devices at the Table: the Mint's progress, the owner's hold, the device's card and what it
// reads. The catalog's Mint family draws each part from the host's own `room.devices` data.
import { type FormEvent, useState } from "react";
import { TrustedConsentSeal } from "../../components/f08/ConsentSeal";
import { DeviceReading } from "../../components/f10/DeviceReading";
import { MintedAgentCard } from "../../components/f10/MintedAgentCard";
import { MintPipeline } from "../../components/f10/MintPipeline";
import { problemText } from "../api";
import { useTable } from "../context";
import { type Device, deviceIo, readDevices } from "./deviceData";
import "./devices.css";

const quiet = () => {};
const clock = (t: number | null) =>
  t === null ? "" : new Date(t * 1000).toISOString().slice(11, 19);

function Pipeline({ d }: { d: Device }) {
  const p = {
    cost: d.cost === null ? "" : String(d.cost),
    elapsed: d.elapsed ?? 0,
    stages: d.stages.map((s) => ({
      name: s.name,
      state: s.state,
      took: s.took,
      detail: s.took === null ? "" : `${s.took.toFixed(1)} s`,
      artifacts: [],
    })),
  };
  return <MintPipeline p={p} send={quiet} />;
}

function Approve({ d }: { d: Device }) {
  const [problem, setProblem] = useState("");
  const approve = async () => {
    const r = await deviceIo.approve(d.id);
    if (!r.ok) {
      setProblem(problemText(r));
      throw new Error(problemText(r));
    }
    return undefined;
  };
  return (
    <div className="tb-dev-approve">
      <p>
        {d.attacks
          ? `${d.attacks.passed} of ${d.attacks.total} attacks were refused.`
          : "The attack suite ran."}{" "}
        Hold to approve it. The host signs the approval with your own key, and it takes a seat.
      </p>
      <TrustedConsentSeal onApprove={approve} />
      {problem && <p role="alert">{problem}</p>}
    </div>
  );
}

function Seated({ d }: { d: Device }) {
  const card = {
    agent: { name: d.label, version: "1.0.0", runtime: "local", created: d.template },
    health: d.health,
    tools: d.tools,
    readings: d.reading.map((r) => ({
      name: r.field,
      value: r.value,
      unit: r.unit,
      live: d.health === "live",
      action: r.over ? "over its limit" : "",
    })),
  };
  return (
    <>
      <MintedAgentCard p={card} send={quiet} />
      {d.hold && (
        <p className="tb-dev-line" data-state={d.hold.state}>
          Hold {d.hold.start} to {d.hold.end}: <b>{d.hold.state}</b>
          {d.needs[0] ? ` for ${d.needs[0].title}` : ""}
        </p>
      )}
      {d.reading.map((r) => (
        <p key={r.field} className="tb-dev-line" data-over={r.over}>
          {r.field}: <b>{r.value}</b> {r.unit} · limit {r.threshold}
          {r.over ? " · over the limit" : ""}
        </p>
      ))}
      {d.readings.length > 1 && (
        <DeviceReading
          p={{
            series: d.readings.map((r) => ({ value: r.value, t: clock(r.t) })),
            planned: [],
            limits: d.fields.map((f) => f.threshold),
            unit: d.fields[0]?.unit ?? "",
            source: d.id,
            annotations: [],
          }}
          send={quiet}
        />
      )}
      {d.needs.length > 0 && (
        <p className="tb-note">Serves: {d.needs.map((n) => n.title).join(", ")}</p>
      )}
      {d.mine && d.template === "device" && <Frame d={d} />}
    </>
  );
}

function Frame({ d }: { d: Device }) {
  const [state, setState] = useState("");
  const send = async (file: File | undefined) => {
    if (!file) return;
    const form = new FormData();
    form.append("device", d.id);
    form.append("frame", file);
    setState("Reading the display…");
    const r = await deviceIo.frame(form);
    if (!r.ok) return setState(problemText(r));
    const crossed = r.data.rippled.length ? " It crossed its limit, so the room re-plans." : "";
    setState(`Read ${r.data.reading.map((x) => `${x.value} ${x.unit}`).join(", ")}.${crossed}`);
  };
  return (
    <label className="tb-dev-file">
      Send a photo of the display
      <input
        type="file"
        accept="image/*"
        capture="environment"
        onChange={(e) => void send(e.target.files?.[0])}
      />
      {state && <span role="status">{state}</span>}
    </label>
  );
}

function MintForm() {
  const { room } = useTable();
  const [state, setState] = useState("");
  const [open, setOpen] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setState("Uploading…");
    const r = await deviceIo.mint(new FormData(event.currentTarget));
    setState(r.ok ? "The Mint is running on the host." : problemText(r));
    if (r.ok) setOpen(false);
  };
  if (!open)
    return (
      <>
        <button type="button" className="btn tb-quietbtn" onClick={() => setOpen(true)}>
          Bring a device: mint it from a video and a voice note
        </button>
        {state && <p role="status">{state}</p>}
      </>
    );
  return (
    <form className="tb-dev-form" onSubmit={(e) => void submit(e)}>
      <label>
        Name
        <input name="label" maxLength={60} placeholder="What everyone calls it" />
      </label>
      <label>
        What it is
        <select name="template" defaultValue="resource">
          <option value="resource">Something people take turns using</option>
          <option value="device">A display with readings</option>
        </select>
      </label>
      <label>
        The need it serves
        <select name="needs" defaultValue="">
          <option value="">The needs that name it</option>
          {room.needs.map((n) => (
            <option key={n.id} value={n.id}>
              {n.title}
            </option>
          ))}
        </select>
      </label>
      <label>
        Video
        <input name="video" type="file" accept="video/*" capture="environment" required />
      </label>
      <label>
        Voice note (WAV)
        <input name="voice" type="file" accept="audio/wav,.wav" required />
      </label>
      <button type="submit" className="btn">
        Mint it
      </button>
      {state && <p role="status">{state}</p>}
    </form>
  );
}

export function Devices() {
  const { state, room } = useTable();
  const devices = readDevices(state);
  const me = room.seats.find((s) => s.you);
  if (room.phase === "ended" || (!devices.length && !me)) return null;
  return (
    <section className="tb-devices" aria-label="Minted devices">
      <div className="tb-sidehead">
        <span>Devices at the table</span>
        <span className="tb-tag">Minted, read-only plus holds</span>
      </div>
      {devices.map((d) => (
        <article key={d.id} className="tb-dev" data-state={d.state}>
          <h3>
            {d.label} <span className="tb-agenttag">device</span>
          </h3>
          {d.state === "minting" && <Pipeline d={d} />}
          {d.state === "approve" && <Pipeline d={d} />}
          {d.state === "approve" &&
            (d.canApprove ? <Approve d={d} /> : <p>Waiting for its owner's hold.</p>)}
          {d.state === "seated" && <Seated d={d} />}
          {d.state === "failed" && <p role="alert">The Mint stopped: {d.error}</p>}
        </article>
      ))}
      {me && <MintForm />}
    </section>
  );
}
