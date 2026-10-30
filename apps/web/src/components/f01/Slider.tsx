// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { number, str, type ViewProps } from "./shared";

export function Slider({ p, send }: ViewProps) {
  const [value, setValue] = useState(p.value);
  useEffect(() => setValue(p.value), [p.value]);
  const min = number(p.min);
  const max = Math.max(min, number(p.max, 100));
  const range = Array.isArray(value);
  const values = (range ? value.slice(0, 2) : [value]).map((v) =>
    Math.min(max, Math.max(min, number(v, min))),
  );
  const percent = (v: number) => ((v - min) / Math.max(1, max - min)) * 100;
  const start = range ? percent(values[0] ?? min) : 0;
  const end = percent(values.at(-1) ?? min);
  return (
    <div className="f01-slider">
      <output className="st">
        {values.join(" – ")}
        {p.unit ? ` ${str(p.unit)}` : ""}
      </output>
      <div className="f01-slider-track">
        <span className="f01-slider-fill" style={{ left: `${start}%`, width: `${end - start}%` }} />
        {values.map((v, index) => (
          <input
            // biome-ignore lint/suspicious/noArrayIndexKey: fixed lower/upper handles
            key={index}
            type="range"
            aria-label={range ? (index === 0 ? "Lower value" : "Upper value") : "Value"}
            aria-valuetext={`${v}${p.unit ? ` ${str(p.unit)}` : ""}`}
            value={v}
            min={min}
            max={max}
            step={number(p.step, 1)}
            onChange={(event) => {
              const next = [...values];
              next[index] = Math.max(
                index === 1 ? (values[0] ?? min) : min,
                Math.min(
                  index === 0 && range ? (values[1] ?? max) : max,
                  Number(event.target.value),
                ),
              );
              const updated = range ? next : next[0];
              setValue(updated);
              send("change", { value: updated, ...(p.unit ? { unit: p.unit } : {}) });
            }}
          />
        ))}
      </div>
    </div>
  );
}
