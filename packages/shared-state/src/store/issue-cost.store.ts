/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { makeAutoObservable, runInAction } from "mobx";
import type { EUserPermissions, TIssueCost, TIssueWorklog, TProjectCostReport } from "@plane/types";

export type TIssueWorklogPayload = Pick<TIssueWorklog, "member_id" | "work_date" | "person_days" | "description">;

export type TIssueCostApi = {
  getCost: (workspaceSlug: string, projectId: string, issueId: string) => Promise<TIssueCost>;
  updateEstimate: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    estimatedPersonDays: string | null
  ) => Promise<TIssueCost>;
  getWorklogs: (workspaceSlug: string, projectId: string, issueId: string) => Promise<TIssueWorklog[]>;
  createWorklog: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    payload: TIssueWorklogPayload
  ) => Promise<TIssueWorklog>;
  updateWorklog: (
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    worklogId: string,
    payload: Partial<TIssueWorklogPayload>
  ) => Promise<TIssueWorklog>;
  deleteWorklog: (workspaceSlug: string, projectId: string, issueId: string, worklogId: string) => Promise<void>;
  getProjectReport: (workspaceSlug: string, projectId: string, month: string) => Promise<TProjectCostReport>;
};

export const canAccessIssueCost = (role: EUserPermissions | undefined): boolean => role === 20 || role === 15;

export const isActualWorkConfirmationRequired = (error: unknown): boolean =>
  (error as { code?: string } | null)?.code === "ACTUAL_WORK_CONFIRMATION_REQUIRED";

export class IssueCostStore {
  costs: Record<string, TIssueCost | undefined> = {};
  worklogs: Record<string, TIssueWorklog[] | undefined> = {};
  reports: Record<string, TProjectCostReport | undefined> = {};
  readonly api: TIssueCostApi;

  constructor(api: TIssueCostApi) {
    this.api = api;
    makeAutoObservable(this, { api: false }, { autoBind: true });
  }

  async fetchCost(workspaceSlug: string, projectId: string, issueId: string) {
    const cost = await this.api.getCost(workspaceSlug, projectId, issueId);
    runInAction(() => {
      this.costs[issueId] = cost;
    });
    return cost;
  }

  async updateEstimate(workspaceSlug: string, projectId: string, issueId: string, value: string | null) {
    const cost = await this.api.updateEstimate(workspaceSlug, projectId, issueId, value);
    runInAction(() => {
      this.costs[issueId] = cost;
    });
    return cost;
  }

  async fetchWorklogs(workspaceSlug: string, projectId: string, issueId: string) {
    const worklogs = await this.api.getWorklogs(workspaceSlug, projectId, issueId);
    runInAction(() => {
      this.worklogs[issueId] = worklogs;
    });
    return worklogs;
  }

  async createWorklog(workspaceSlug: string, projectId: string, issueId: string, payload: TIssueWorklogPayload) {
    const worklog = await this.api.createWorklog(workspaceSlug, projectId, issueId, payload);
    runInAction(() => {
      this.worklogs[issueId] = [worklog, ...(this.worklogs[issueId] ?? [])];
    });
    return worklog;
  }

  async updateWorklog(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    worklogId: string,
    payload: Partial<TIssueWorklogPayload>
  ) {
    const worklog = await this.api.updateWorklog(workspaceSlug, projectId, issueId, worklogId, payload);
    runInAction(() => {
      this.worklogs[issueId] = (this.worklogs[issueId] ?? []).map((item) => (item.id === worklogId ? worklog : item));
    });
    return worklog;
  }

  async deleteWorklog(workspaceSlug: string, projectId: string, issueId: string, worklogId: string) {
    await this.api.deleteWorklog(workspaceSlug, projectId, issueId, worklogId);
    runInAction(() => {
      this.worklogs[issueId] = (this.worklogs[issueId] ?? []).filter((item) => item.id !== worklogId);
    });
  }

  async fetchProjectReport(workspaceSlug: string, projectId: string, month: string) {
    const report = await this.api.getProjectReport(workspaceSlug, projectId, month);
    runInAction(() => {
      this.reports[`${projectId}:${month}`] = report;
    });
    return report;
  }
}
