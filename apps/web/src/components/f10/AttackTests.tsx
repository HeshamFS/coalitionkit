// SPDX-License-Identifier: Apache-2.0
import { type Props, rows, type Send, text } from "../f08/shared";
import "../../styles/f10.css";
export function AttackTests({ p, send }: { p: Props; send: Send }) {
  const tests = rows(p.tests);
  const visible = tests.filter((test, i) => i < 3 || test.state !== "passed");
  const passed = tests.filter((t) => t.state === "passed").length;
  const failed = tests.filter((t) => t.state === "failed").length;
  const running = tests.filter((t) => t.state === "running").length;
  return (
    <>
      <ul className="f10-tests">
        {visible.map((test, i) => (
          <li className="row" key={text(test.name) || `${i}`}>
            {test.state === "running" ? (
              <span className="spinner f10-test-running" />
            ) : (
              <svg
                className={`ico ico-sm ${test.state === "failed" ? "family-bad" : "family-ok"}`}
                viewBox="0 0 24 24"
                aria-label={text(test.state)}
              >
                <title>{text(test.state)}</title>
                <path d={test.state === "failed" ? "M6 6l12 12M18 6L6 18" : "M5 12l5 5 9-10"} />
              </svg>
            )}
            <span className="small grow">{text(test.name)}</span>
            {test.state === "failed" && <span className="badge f10-test-fail">fail</span>}
          </li>
        ))}
      </ul>
      <div className="row small">
        <span className="num">
          {passed} / {tests.length} pass{failed > 0 && ` · ${failed} fail`}
          {running > 0 && ` · ${running} running`}
        </span>
        <button className="f10-link h-right" type="button" onClick={() => send("tests.rerun")}>
          Fix and re-run
        </button>
      </div>
    </>
  );
}
