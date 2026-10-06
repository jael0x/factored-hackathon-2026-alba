// POST /messages and the consultant close answer within 30 seconds, or 503 (ARCHITECTURE.md "HTTP contract").
export const CYCLE_WAIT_MS = 35_000;

const WEB_URL = "ALBA_WEB_URL";

export function webUrl(): string {
  const url = process.env[WEB_URL];
  if (url === undefined || url === "") {
    throw new Error(`${WEB_URL} is not set: run the browser flows through scripts/e2e.sh`);
  }
  return url;
}
