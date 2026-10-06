export function lastFour(value: string): string {
  return value.slice(-4);
}

const AMOUNT = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function amountParts(value: number): { whole: string; cents: string } {
  const [whole, cents] = AMOUNT.format(value).split(".");
  return { whole, cents };
}

export function formatAmount(value: number): string {
  return AMOUNT.format(value);
}

// A date-only value is read and written in UTC, so the day does not move with the browser's time zone.
export function formatDate(isoDate: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "long", timeZone: "UTC" }).format(new Date(`${isoDate}T00:00:00Z`));
}

// An instant is shown where the reader is, to the second: events written together share it.
export function formatDateTime(isoInstant: string, locale: string, timeZone?: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "medium", timeZone }).format(
    new Date(isoInstant),
  );
}

export function fullName(person: { first_name: string; last_name: string }): string {
  return `${person.first_name} ${person.last_name}`;
}
