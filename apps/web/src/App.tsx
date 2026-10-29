// SPDX-License-Identifier: Apache-2.0
import { useEffect, useState } from "react";
import { readConfig, scrubAddress } from "./feed/config";
import { FeedProvider } from "./feed/useFeed";
import { Gallery } from "./gallery/Gallery";
import { RoomView } from "./RoomView";
import { SignIn } from "./SignIn";

export function App() {
  const [config, setConfig] = useState(() => readConfig());
  useEffect(() => scrubAddress(), []);
  if (location.pathname.startsWith("/gallery")) return <Gallery />;
  if (!config) return <SignIn onDone={() => setConfig(readConfig())} />;
  return (
    <FeedProvider config={config}>
      <RoomView />
    </FeedProvider>
  );
}
