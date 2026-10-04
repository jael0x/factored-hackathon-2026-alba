export type StoredItems = {
  read(key: string): string | null;
  write(key: string, value: string): void;
  remove(key: string): void;
};

// Blocked site storage throws on access, and a full one throws on write. What the app keeps here is a per-tab
// convenience (the language choice, the session across a reload), so a blocked area reads as empty, drops writes,
// and the caller goes on from memory.
function storedItems(area: () => Storage): StoredItems {
  return {
    read(key) {
      try {
        return area().getItem(key);
      } catch {
        return null;
      }
    },
    write(key, value) {
      try {
        area().setItem(key, value);
      } catch {
        return;
      }
    },
    remove(key) {
      try {
        area().removeItem(key);
      } catch {
        return;
      }
    },
  };
}

export const browserItems = storedItems(() => window.localStorage);

export const tabItems = storedItems(() => window.sessionStorage);
