import type { components } from "./api/schema";

export type Role = components["schemas"]["Role"];

export const HOME_PATH: Record<Role, string> = { customer: "/", agent: "/agent" };

export const LOGIN_PATH: Record<Role, string> = { customer: "/login", agent: "/agent/login" };
