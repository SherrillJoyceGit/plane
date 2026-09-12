import { describe, expect, it, vi } from "vitest";
import { EUserPermissions } from "@plane/types";
import type { TIssueCost, TIssueWorklog, TProjectCostReport } from "@plane/types";
import {
  canAccessIssueCost,
  isActualWorkConfirmationRequired,
  IssueCostStore,
  resolveWorklogMemberId,
  type TIssueCostApi,
} from "./issue-cost.store";

const cost: TIssueCost = {
  issue_id: "issue",
  cost_root_id: "issue",
  estimated_person_days: "2.0",
  estimate_locked_at: null,
  actual_person_days: "0.5",
  variance_person_days: "-1.5",
  zero_actual_confirmed_at: null,
  zero_actual_confirmed_by: null,
  can_log_actual: true,
};

const worklog: TIssueWorklog = {
  id: "worklog",
  member_id: "member",
  work_date: "2026-09-12",
  person_days: "0.5",
  description: "Work",
  created_at: "2026-09-12T00:00:00Z",
  updated_at: "2026-09-12T00:00:00Z",
  created_by: "member",
  updated_by: null,
};

const report = { month: "2026-09", summary: {}, issues: [] } as unknown as TProjectCostReport;

const createApi = (): TIssueCostApi => ({
  getCost: vi.fn().mockResolvedValue(cost),
  updateEstimate: vi.fn().mockResolvedValue({ ...cost, estimated_person_days: "3.0" }),
  getWorklogs: vi.fn().mockResolvedValue([worklog]),
  createWorklog: vi.fn().mockResolvedValue(worklog),
  updateWorklog: vi.fn().mockResolvedValue({ ...worklog, person_days: "1.0" }),
  deleteWorklog: vi.fn().mockResolvedValue(undefined),
  getProjectReport: vi.fn().mockResolvedValue(report),
});

describe("IssueCostStore", () => {
  it("stores cost, worklogs, and reports by their stable keys", async () => {
    const store = new IssueCostStore(createApi());
    await store.fetchCost("workspace", "project", "issue");
    await store.fetchWorklogs("workspace", "project", "issue");
    await store.fetchProjectReport("workspace", "project", "2026-09");
    expect(store.costs.issue).toEqual(cost);
    expect(store.worklogs.issue).toEqual([worklog]);
    expect(store.reports["project:2026-09"]).toEqual(report);
  });

  it("updates and removes worklogs without leaving stale entries", async () => {
    const store = new IssueCostStore(createApi());
    store.worklogs.issue = [worklog];
    await store.updateWorklog("workspace", "project", "issue", "worklog", { person_days: "1.0" });
    expect(store.worklogs.issue?.[0].person_days).toBe("1.0");
    await store.deleteWorklog("workspace", "project", "issue", "worklog");
    expect(store.worklogs.issue).toEqual([]);
  });
});

describe("cost permissions and completion", () => {
  it("allows Admin and Member while excluding Guest", () => {
    expect(canAccessIssueCost(EUserPermissions.ADMIN)).toBe(true);
    expect(canAccessIssueCost(EUserPermissions.MEMBER)).toBe(true);
    expect(canAccessIssueCost(EUserPermissions.GUEST)).toBe(false);
  });

  it("recognizes only the stable completion confirmation code", () => {
    expect(isActualWorkConfirmationRequired({ code: "ACTUAL_WORK_CONFIRMATION_REQUIRED" })).toBe(true);
    expect(isActualWorkConfirmationRequired({ code: "OTHER" })).toBe(false);
  });

  it("uses the current member when assignees change after the cost panel opens", () => {
    expect(resolveWorklogMemberId(false, "stale-assignee", "current-member", ["current-member"])).toBe(
      "current-member"
    );
    expect(resolveWorklogMemberId(false, "stale-assignee", "current-member", ["other-member"])).toBe("");
    expect(resolveWorklogMemberId(true, "selected-member", "current-member", ["current-member"])).toBe(
      "selected-member"
    );
  });
});
