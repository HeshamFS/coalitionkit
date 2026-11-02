// SPDX-License-Identifier: Apache-2.0
import "@fontsource-variable/geist";
import "@fontsource-variable/jetbrains-mono";
import "@fontsource/instrument-serif";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/ext.css";
import "./styles/app.css";
import "./styles/lens.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { PageScroll } from "./shell/PageScroll";
import { applyStoredTheme } from "./shell/theme";

applyStoredTheme();

const el = document.getElementById("root");
if (el) {
  createRoot(el).render(
    <StrictMode>
      <App />
      <PageScroll />
    </StrictMode>,
  );
}
