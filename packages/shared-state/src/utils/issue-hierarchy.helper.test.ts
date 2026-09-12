import { describe, expect, it } from "vitest";
import { canIssueHaveChildren, canIssueSetParent, getAllowedIssueTypeNames } from "./issue-hierarchy.helper";

describe("work item two-level hierarchy", () => {
  it("limits child types to Task and Bug", () => {
    expect(getAllowedIssueTypeNames(true, false)).toEqual(["Task", "Bug"]);
  });

  it("prevents a parent with children from becoming Bug", () => {
    expect(getAllowedIssueTypeNames(false, true)).toEqual(["Requirement", "Task"]);
  });

  it("allows all standard types for a leaf at the top level", () => {
    expect(getAllowedIssueTypeNames(false, false)).toEqual(["Requirement", "Task", "Bug"]);
  });

  it("only lets top-level Requirement and Task own children", () => {
    expect(canIssueHaveChildren("Requirement", null)).toBe(true);
    expect(canIssueHaveChildren("Task", null)).toBe(true);
    expect(canIssueHaveChildren("Bug", null)).toBe(false);
    expect(canIssueHaveChildren("Task", "parent")).toBe(false);
  });

  it("only lets leaf Task and Bug select a parent", () => {
    expect(canIssueSetParent("Task", null, 0)).toBe(true);
    expect(canIssueSetParent("Bug", null, 0)).toBe(true);
    expect(canIssueSetParent("Requirement", null, 0)).toBe(false);
    expect(canIssueSetParent("Task", null, 1)).toBe(false);
    expect(canIssueSetParent("Task", "parent", 0)).toBe(true);
  });
});
