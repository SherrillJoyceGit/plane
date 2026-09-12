/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { API_BASE_URL } from "@plane/constants";
import { isActualWorkConfirmationRequired } from "@plane/shared-state";
import type { TIssueCost, TIssueWorklog, TProjectCostReport } from "@plane/types";
import { APIService } from "@/services/api.service";

export type TWorklogPayload = Pick<TIssueWorklog, "member_id" | "work_date" | "person_days" | "description">;
export const retryAfterActualWorkConfirmation = async (
  error: unknown,
  message: string,
  confirm: () => Promise<void>,
  retry: () => Promise<void>
): Promise<boolean> => {
  if (!isActualWorkConfirmationRequired(error)) return false;
  if (!window.confirm(message)) return true;
  await confirm();
  await retry();
  return true;
};

export class IssueCostService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  getCost(workspaceSlug: string, projectId: string, issueId: string): Promise<TIssueCost> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/cost/`)
      .then((response) => response.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  updateEstimate(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    estimatedPersonDays: string | null
  ): Promise<TIssueCost> {
    return this.patch(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/cost/`, {
      estimated_person_days: estimatedPersonDays,
    })
      .then((response) => response.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  getWorklogs(workspaceSlug: string, projectId: string, issueId: string): Promise<TIssueWorklog[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/`)
      .then((response) => response.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  createWorklog(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    payload: TWorklogPayload
  ): Promise<TIssueWorklog> {
    return this.post(`/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/`, payload)
      .then((response) => response.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  updateWorklog(
    workspaceSlug: string,
    projectId: string,
    issueId: string,
    worklogId: string,
    payload: Partial<TWorklogPayload>
  ): Promise<TIssueWorklog> {
    return this.patch(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/${worklogId}/`,
      payload
    )
      .then((response) => response.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  deleteWorklog(workspaceSlug: string, projectId: string, issueId: string, worklogId: string): Promise<void> {
    return this.delete(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/worklogs/${worklogId}/`
    )
      .then(() => undefined)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  confirmNoActualWork(workspaceSlug: string, projectId: string, issueId: string): Promise<void> {
    return this.post(
      `/api/workspaces/${workspaceSlug}/projects/${projectId}/issues/${issueId}/actual-work-confirmation/`,
      { confirm_no_actual_work: true }
    )
      .then(() => undefined)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  getProjectReport(workspaceSlug: string, projectId: string, month: string): Promise<TProjectCostReport> {
    return this.get(`/api/workspaces/${workspaceSlug}/projects/${projectId}/cost-report/`, { params: { month } })
      .then((response) => response.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
