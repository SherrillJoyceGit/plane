import { describe, expect, it, vi } from "vitest";
import type { TIssueType } from "@plane/types";
import { getIssueTypeDisplayName, IssueTypeStore } from "./issue-type.store";

const issueTypes: TIssueType[] = [
  {
    id: "task",
    name: "Task",
    description: "",
    logo_props: { icon: "SquareCheckBig", color: "#16A34A" },
    is_default: true,
    is_active: true,
    level: 2,
  },
];

describe("IssueTypeStore", () => {
  it("caches project types and exposes the default type", async () => {
    const fetcher = vi.fn().mockResolvedValue(issueTypes);
    const store = new IssueTypeStore(fetcher);

    await Promise.all([
      store.fetchProjectIssueTypes("workspace", "project"),
      store.fetchProjectIssueTypes("workspace", "project"),
    ]);
    await store.fetchProjectIssueTypes("workspace", "project");

    expect(fetcher).toHaveBeenCalledOnce();
    expect(store.getProjectIssueTypes("project")).toEqual(issueTypes);
    expect(store.getDefaultIssueTypeId("project")).toBe("task");
    expect(store.getIssueTypeById("task", "project")).toEqual(issueTypes[0]);
  });

  it("keeps project caches isolated", async () => {
    const store = new IssueTypeStore(async (_workspaceSlug, projectId) => [
      { ...issueTypes[0], id: `${projectId}-task` },
    ]);

    await store.fetchProjectIssueTypes("workspace", "first");
    await store.fetchProjectIssueTypes("workspace", "second");

    expect(store.getDefaultIssueTypeId("first")).toBe("first-task");
    expect(store.getDefaultIssueTypeId("second")).toBe("second-task");
  });
});

describe("getIssueTypeDisplayName", () => {
  it("localizes built-in names only for Chinese locales", () => {
    expect(getIssueTypeDisplayName("Requirement", "zh-CN")).toBe("需求");
    expect(getIssueTypeDisplayName("Bug", "zh-TW")).toBe("缺陷");
    expect(getIssueTypeDisplayName("Task", "en")).toBe("Task");
    expect(getIssueTypeDisplayName("Task", "zh-HK")).toBe("Task");
    expect(getIssueTypeDisplayName("Custom", "zh-CN")).toBe("Custom");
  });
});
