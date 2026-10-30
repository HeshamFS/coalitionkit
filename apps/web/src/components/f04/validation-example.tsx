// SPDX-License-Identifier: Apache-2.0
import { One } from "../../gallery/Drawn";

export function ValidationExample() {
  return (
    <div className="f04-validation-example">
      <One
        component="ValidationSummary"
        props={{
          errors: [
            { field: "complete_by", text: "Complete by is in the past" },
            { field: "items", text: "Items: pick one" },
          ],
        }}
      />
      <One
        component="TextField"
        props={{ label: "Complete by", value: { path: "/time" }, error: { path: "/error" } }}
        data={{ time: "Yesterday 10:00", error: "Pick a time after now (22:21)" }}
      />
      <div className="f04-validation-choice">
        <span>Items</span>
        <One
          component="SegmentedControl"
          props={{
            options: [
              { id: "none", label: "None" },
              { id: "small", label: "Small" },
              { id: "large", label: "Large" },
            ],
            value: { path: "/choice" },
          }}
          data={{ choice: "" }}
        />
      </div>
    </div>
  );
}
