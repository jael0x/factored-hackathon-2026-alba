import type { components } from "./api/schema";

export type Role = components["schemas"]["Role"];

export const HOME_PATH: Record<Role, string> = { customer: "/", consultant: "/consultant" };

export const LOGIN_PATH: Record<Role, string> = { customer: "/login", consultant: "/consultant/login" };

export function isRole(value: unknown): value is Role {
  return typeof value === "string" && Object.hasOwn(HOME_PATH, value);
}

export const CASE_PATH = "/case";

export function casePath(processId: string): string {
  return `${CASE_PATH}/${processId}`;
}
