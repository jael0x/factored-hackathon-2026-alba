export function lastFour(value: string): string {
  return value.slice(-4);
}

const AMOUNT = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function amountParts(value: number): { whole: string; cents: string } {
  const [whole, cents] = AMOUNT.format(value).split(".");
  return { whole, cents };
}

export function fullName(person: { first_name: string; last_name: string }): string {
  return `${person.first_name} ${person.last_name}`;
}
