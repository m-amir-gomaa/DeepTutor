/** Reserve the popup synchronously, before asynchronous OAuth discovery. */
export async function openMcpAuthorization(
  start: () => Promise<string>,
  browser: Pick<Window, "open" | "location"> = window,
): Promise<Window | null> {
  const popup = browser.open("about:blank", "deeptutor-mcp-authorization");
  if (popup) popup.opener = null;
  try {
    const url = await start();
    if (!url) throw new Error("no authorization URL");
    if (popup) popup.location.replace(url);
    else browser.location.assign(url);
    return popup;
  } catch (error) {
    popup?.close();
    throw error;
  }
}
