export function lastFour(value: string): string {
  return value.slice(-4);
}

export function fullName(person: { first_name: string; last_name: string }): string {
  return `${person.first_name} ${person.last_name}`;
}
