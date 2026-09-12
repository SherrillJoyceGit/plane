/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect, useMemo, useState } from "react";
import { observer } from "mobx-react";
import { LockKeyhole, Pencil, Save, Trash2, X } from "lucide-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { resolveWorklogMemberId } from "@plane/shared-state";
import type { TIssueWorklog } from "@plane/types";
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
import { useIssueType } from "@/hooks/store/use-issue-type";
import { useMember } from "@/hooks/store/use-member";
import { useProjectState } from "@/hooks/store/use-project-state";
import { useUser, useUserPermissions } from "@/hooks/store/user";
import { issueCostStore } from "@/store/issue-cost.store";
const today = () => {
  const date = new Date();
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
};

const errorMessage = (error: unknown, fallback: string) => {
  if (!error || typeof error !== "object") return fallback;
  const value = Object.values(error as Record<string, unknown>)[0];
  if (Array.isArray(value)) return String(value[0] ?? fallback);
  return typeof value === "string" ? value : fallback;
};

type Props = {
  workspaceSlug: string;
  projectId: string;
  issueId: string;
  disabled: boolean;
};

export const IssueCostSection = observer(function IssueCostSection(props: Props) {
  const { workspaceSlug, projectId, issueId, disabled } = props;
  const { t } = useTranslation();
  const { data: currentUser } = useUser();
  const { allowPermissions } = useUserPermissions();
  const { getUserDetails } = useMember();
  const { getIssueTypeById } = useIssueType();
  const { getStateById } = useProjectState();
  const {
    issue: { getIssueById },
  } = useIssueDetail();
  const issue = getIssueById(issueId);
  const canView = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug,
    projectId
  );
  const isAdmin = allowPermissions([EUserPermissions.ADMIN], EUserPermissionsLevel.PROJECT, workspaceSlug, projectId);
  const cost = issueCostStore.costs[issueId];
  const worklogs = issueCostStore.worklogs[issueId] ?? [];
  const [estimate, setEstimate] = useState("");
  const [memberId, setMemberId] = useState("");
  const [workDate, setWorkDate] = useState(today());
  const [personDays, setPersonDays] = useState<"0.5" | "1.0">("0.5");
  const [description, setDescription] = useState("");
  const [editing, setEditing] = useState<TIssueWorklog | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (canView) void issueCostStore.fetchCost(workspaceSlug, projectId, issueId);
  }, [canView, issueId, projectId, workspaceSlug]);
  useEffect(() => {
    if (canView && cost?.can_log_actual) void issueCostStore.fetchWorklogs(workspaceSlug, projectId, issueId);
  }, [canView, cost?.can_log_actual, issueId, projectId, workspaceSlug]);
  useEffect(() => setEstimate(cost?.estimated_person_days ?? ""), [cost?.estimated_person_days]);
  useEffect(() => {
    if (!issue || memberId) return;
    if (currentUser?.id && issue.assignee_ids.includes(currentUser.id)) setMemberId(currentUser.id);
    else if (isAdmin) setMemberId(issue.assignee_ids[0] ?? "");
  }, [currentUser?.id, isAdmin, issue, memberId]);

  const issueType = getIssueTypeById(issue?.type_id, projectId);
  const isEstimatable = !issue?.parent_id && ["Requirement", "Task"].includes(issueType?.name ?? "");
  const stateGroup = getStateById(issue?.state_id)?.group;
  const worklogMemberId = resolveWorklogMemberId(isAdmin, memberId, currentUser?.id, issue?.assignee_ids ?? []);
  const canCreateWorklog =
    !disabled && cost?.can_log_actual && ["started", "completed"].includes(stateGroup ?? "") && !!worklogMemberId;
  const assignees = useMemo(
    () => issue?.assignee_ids.map((id) => ({ id, name: getUserDetails(id)?.display_name ?? id })) ?? [],
    [getUserDetails, issue?.assignee_ids]
  );

  if (!canView || !issue || !cost) return null;

  const notifyError = (error: unknown) =>
    setToast({
      type: TOAST_TYPE.ERROR,
      title: t("common.error.label"),
      message: errorMessage(error, t("issue.cost.error")),
    });

  const saveEstimate = async () => {
    setSubmitting(true);
    try {
      await issueCostStore.updateEstimate(workspaceSlug, projectId, issueId, estimate || null);
    } catch (error) {
      notifyError(error);
    } finally {
      setSubmitting(false);
    }
  };

  const createWorklog = async () => {
    if (!worklogMemberId) return;
    setSubmitting(true);
    try {
      await issueCostStore.createWorklog(workspaceSlug, projectId, issueId, {
        member_id: worklogMemberId,
        work_date: workDate,
        person_days: personDays,
        description,
      });
      setDescription("");
      await issueCostStore.fetchCost(workspaceSlug, projectId, issueId);
    } catch (error) {
      notifyError(error);
    } finally {
      setSubmitting(false);
    }
  };

  const saveWorklog = async () => {
    if (!editing) return;
    setSubmitting(true);
    try {
      await issueCostStore.updateWorklog(workspaceSlug, projectId, issueId, editing.id, {
        work_date: editing.work_date,
        person_days: editing.person_days,
        description: editing.description,
      });
      setEditing(null);
      await issueCostStore.fetchCost(workspaceSlug, projectId, issueId);
    } catch (error) {
      notifyError(error);
    } finally {
      setSubmitting(false);
    }
  };

  const deleteWorklog = async (worklogId: string) => {
    setSubmitting(true);
    try {
      await issueCostStore.deleteWorklog(workspaceSlug, projectId, issueId, worklogId);
      await issueCostStore.fetchCost(workspaceSlug, projectId, issueId);
    } catch (error) {
      notifyError(error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="border-t border-subtle pt-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="text-body-sm-medium text-primary">{t("issue.cost.title")}</h3>
        <span className="text-caption-sm-regular text-secondary">
          {t("issue.cost.actual_total")}: {cost.actual_person_days}
        </span>
      </div>

      {isEstimatable && (
        <div className="mb-4 flex flex-wrap items-end gap-2">
          <label className="flex min-w-40 flex-col gap-1 text-caption-sm-medium text-secondary">
            {t("issue.cost.estimate")}
            <input
              className="h-8 rounded border border-subtle bg-surface-1 px-2 text-body-sm-regular text-primary disabled:cursor-not-allowed disabled:opacity-60"
              type="number"
              min="0.5"
              step="0.5"
              value={estimate}
              disabled={disabled || !!cost.estimate_locked_at || submitting}
              onChange={(event) => setEstimate(event.target.value)}
            />
          </label>
          {!cost.estimate_locked_at && !disabled && (
            <button
              type="button"
              className="bg-primary-100 h-8 rounded px-3 text-caption-sm-medium text-on-color disabled:opacity-50"
              disabled={submitting}
              onClick={saveEstimate}
            >
              {t("save")}
            </button>
          )}
          {cost.estimate_locked_at && (
            <span className="flex h-8 items-center gap-1 text-caption-sm-regular text-secondary">
              <LockKeyhole className="h-3.5 w-3.5" /> {t("issue.cost.locked")}
            </span>
          )}
        </div>
      )}

      {!cost.can_log_actual ? (
        <p className="text-body-sm-regular text-secondary">{t("issue.cost.log_on_children")}</p>
      ) : (
        <div className="space-y-3">
          {worklogs.length > 0 && (
            <div className="divide-y divide-subtle border-y border-subtle">
              {worklogs.map((worklog) => {
                const canManage = isAdmin || worklog.member_id === currentUser?.id;
                const isEditing = editing?.id === worklog.id;
                return (
                  <div
                    key={worklog.id}
                    className="flex min-h-10 flex-wrap items-center gap-2 py-2 text-body-sm-regular"
                  >
                    <span className="min-w-28 text-primary">
                      {getUserDetails(worklog.member_id)?.display_name ?? worklog.member_id}
                    </span>
                    {isEditing ? (
                      <>
                        <input
                          type="date"
                          max={today()}
                          className="h-8 rounded border border-subtle bg-surface-1 px-2"
                          value={editing.work_date}
                          onChange={(event) => setEditing({ ...editing, work_date: event.target.value })}
                        />
                        <select
                          className="h-8 rounded border border-subtle bg-surface-1 px-2"
                          value={editing.person_days}
                          onChange={(event) =>
                            setEditing({ ...editing, person_days: event.target.value as "0.5" | "1.0" })
                          }
                        >
                          <option value="0.5">0.5</option>
                          <option value="1.0">1.0</option>
                        </select>
                        <input
                          className="h-8 min-w-44 flex-1 rounded border border-subtle bg-surface-1 px-2"
                          value={editing.description}
                          onChange={(event) => setEditing({ ...editing, description: event.target.value })}
                        />
                        <button type="button" title={t("save")} onClick={saveWorklog} disabled={submitting}>
                          <Save className="h-4 w-4" />
                        </button>
                        <button type="button" title={t("cancel")} onClick={() => setEditing(null)}>
                          <X className="h-4 w-4" />
                        </button>
                      </>
                    ) : (
                      <>
                        <span className="text-secondary">{worklog.work_date}</span>
                        <span className="w-16 text-primary">{worklog.person_days}</span>
                        <span className="min-w-24 flex-1 text-secondary">{worklog.description || "-"}</span>
                        {canManage && !disabled && (
                          <>
                            <button type="button" title={t("edit")} onClick={() => setEditing({ ...worklog })}>
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              title={t("delete")}
                              disabled={submitting}
                              onClick={() => deleteWorklog(worklog.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </>
                        )}
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {canCreateWorklog && (
            <div className="flex flex-wrap items-end gap-2">
              {isAdmin && (
                <label className="flex flex-col gap-1 text-caption-sm-medium text-secondary">
                  {t("issue.cost.member")}
                  <select
                    className="h-8 rounded border border-subtle bg-surface-1 px-2 text-primary"
                    value={memberId}
                    onChange={(event) => setMemberId(event.target.value)}
                  >
                    {assignees.map((assignee) => (
                      <option key={assignee.id} value={assignee.id}>
                        {assignee.name}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label className="flex flex-col gap-1 text-caption-sm-medium text-secondary">
                {t("issue.cost.work_date")}
                <input
                  type="date"
                  max={today()}
                  className="h-8 rounded border border-subtle bg-surface-1 px-2 text-primary"
                  value={workDate}
                  onChange={(event) => setWorkDate(event.target.value)}
                />
              </label>
              <label className="flex flex-col gap-1 text-caption-sm-medium text-secondary">
                {t("issue.cost.person_days")}
                <select
                  className="h-8 rounded border border-subtle bg-surface-1 px-2 text-primary"
                  value={personDays}
                  onChange={(event) => setPersonDays(event.target.value as "0.5" | "1.0")}
                >
                  <option value="0.5">0.5</option>
                  <option value="1.0">1.0</option>
                </select>
              </label>
              <label className="flex min-w-44 flex-1 flex-col gap-1 text-caption-sm-medium text-secondary">
                {t("issue.cost.description")}
                <input
                  className="h-8 rounded border border-subtle bg-surface-1 px-2 text-primary"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                />
              </label>
              <button
                type="button"
                className="bg-primary-100 h-8 rounded px-3 text-caption-sm-medium text-on-color disabled:opacity-50"
                disabled={submitting}
                onClick={createWorklog}
              >
                {t("issue.cost.add_worklog")}
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
});
