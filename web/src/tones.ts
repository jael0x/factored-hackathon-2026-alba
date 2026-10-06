import type { components } from "./api/schema";

type Outcome = components["schemas"]["Outcome"];
type ProcessState = components["schemas"]["ProcessState"];

export type Tone = "green" | "stop" | "clay" | "amber" | "slate" | "ink";

// DESIGN.md "Tones": the one map from an outcome or a state to its look.
export const OUTCOME_TONE: Record<Outcome, Tone> = {
  PREQUALIFIED: "green",
  NOT_PREQUALIFIED: "stop",
  REFER: "clay",
  NEEDS_INFO: "amber",
};

export const STATE_TONE: Record<ProcessState, Tone> = {
  ai_active: "slate",
  human_active: "clay",
  ended: "ink",
};
