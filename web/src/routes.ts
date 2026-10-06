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

const CONSULTANT_CASE_SEGMENT = "case";

export const CONSULTANT_CASE_ROUTE = `${CONSULTANT_CASE_SEGMENT}/:processId`;

export function consultantCasePath(processId: string): string {
  return `${HOME_PATH.consultant}/${CONSULTANT_CASE_SEGMENT}/${processId}`;
}

const TRACE_SEGMENT = "trace";

export const CONSULTANT_TRACE_ROUTE = `${CONSULTANT_CASE_ROUTE}/${TRACE_SEGMENT}`;

export function consultantTracePath(processId: string): string {
  return `${consultantCasePath(processId)}/${TRACE_SEGMENT}`;
}
