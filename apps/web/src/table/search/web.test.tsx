// SPDX-License-Identifier: Apache-2.0
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { readLinks, readSearches } from "./links";
import { WebSources } from "./WebSources";

describe("web sources", () => {
  it("keeps only http(s) links", () => {
    const links = readLinks([
      { title: "A hall", url: "https://example.org/hall" },
      { title: "Bad", url: "javascript:alert(1)" },
      { url: "http://example.net/x" },
      "nope",
    ]);
    expect(links).toEqual([
      { title: "A hall", url: "https://example.org/hall" },
      { title: "example.net", url: "http://example.net/x" },
    ]);
    expect(readLinks(null)).toEqual([]);
  });

  it("shows the links and the screened queries", () => {
    const searches = readSearches([
      {
        id: "s1",
        seat: "p1",
        need: "n1",
        query: "a hall for us",
        ran: ["a hall"],
        provider: "meta",
        count: 2,
        ms: 9200,
      },
      {
        id: "s2",
        seat: "p1",
        need: "n1",
        query: "",
        provider: "meta",
        stopped: "it holds a street address",
      },
    ]);
    render(
      <WebSources
        links={readLinks([{ title: "A hall", url: "https://example.org/hall" }])}
        searches={searches}
      />,
    );
    const link = screen.getByRole("link", { name: "A hall" });
    expect(link.getAttribute("href")).toBe("https://example.org/hall");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.getByText('Searched "a hall" (meta): 2 found, 9.2 s.')).toBeTruthy();
    expect(screen.getByText("A search was refused: it holds a street address.")).toBeTruthy();
  });

  it("draws nothing without links in the compact form", () => {
    const { container } = render(<WebSources links={[]} compact />);
    expect(container.innerHTML).toBe("");
  });
});
