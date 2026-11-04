import test from "node:test";
import assert from "node:assert/strict";
import { openMcpAuthorization } from "../lib/mcp-authorization";

function fixture(blocked = false) {
  const events: string[] = [];
  const popup = { opener: {} as unknown, location: { replace: (url: string) => events.push(`navigate:${url}`) }, close: () => events.push("close") };
  const browser = {
    open: () => { events.push("open"); return blocked ? null : popup; },
    location: { assign: (url: string) => events.push(`fallback:${url}`) },
  } as unknown as Pick<Window, "open" | "location">;
  return { events, popup, browser };
}
test("OAuth popup is reserved before waiting for discovery", async () => {
  const { events, popup, browser } = fixture();
  let resolve!: (url: string) => void;
  const pending = new Promise<string>(done => { resolve = done; });
  const completion = openMcpAuthorization(() => { events.push("discovery"); return pending; }, browser);
  assert.deepEqual(events, ["open", "discovery"]);
  assert.equal(popup.opener, null);
  resolve("https://provider.example.invalid/authorize");
  await completion;
  assert.deepEqual(events, ["open", "discovery", "navigate:https://provider.example.invalid/authorize"]);
});
test("blocked popups use explicit same-tab navigation after discovery", async () => {
  const { events, browser } = fixture(true);
  await openMcpAuthorization(async () => "https://provider.example.invalid/authorize", browser);
  assert.deepEqual(events, ["open", "fallback:https://provider.example.invalid/authorize"]);
});
test("failed discovery closes the reserved window and preserves the error", async () => {
  const { events, browser } = fixture();
  await assert.rejects(openMcpAuthorization(async () => { throw new Error("Fixture discovery failure"); }, browser), /Fixture discovery failure/);
  assert.deepEqual(events, ["open", "close"]);
});
