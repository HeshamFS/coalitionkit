// SPDX-License-Identifier: Apache-2.0
import { Icon } from "../ui/Icon";
export function RoomNavigation({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (tab: string) => void;
}) {
  return (
    <>
      <nav className="room-tabs" aria-label="Room sections">
        {["Stage", "My part", "Plans", "Wiring"].map((tab) => (
          <button
            type="button"
            key={tab}
            aria-current={selected === tab ? "page" : undefined}
            onClick={() => onSelect(tab)}
            data-tab={tab}
          >
            <span className="room-wide-label">{tab}</span>
            <span className="room-phone-label">
              <Icon name={tab === "My part" ? "people" : tab === "Plans" ? "canvas" : "list"} />
              {tab === "Wiring" ? "What happened" : tab}
            </span>
          </button>
        ))}
      </nav>
      <details className="room-view-as">
        <summary className="btn btn-sm">View as…</summary>
        <div className="room-view-menu">
          <button type="button" className="btn btn-sm" onClick={() => onSelect("Lens")}>
            Lens · your part
          </button>
        </div>
      </details>
    </>
  );
}
