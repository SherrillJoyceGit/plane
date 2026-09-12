/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useEffect } from "react";
import { observer } from "mobx-react";
import { EUserPermissions, EUserPermissionsLevel } from "@plane/constants";
import { useTranslation } from "@plane/i18n";
import { Spinner } from "@plane/ui";
import { useUserPermissions } from "@/hooks/store/user";
import { issueCostStore } from "@/store/issue-cost.store";
const currentMonth = () => {
  const date = new Date();
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 7);
};

type Props = {
  workspaceSlug: string;
  projectId: string;
  month: string;
  onMonthChange: (month: string) => void;
};

export const WorkItemCostReport = observer(function WorkItemCostReport(props: Props) {
  const { workspaceSlug, projectId, month, onMonthChange } = props;
  const { t } = useTranslation();
  const { allowPermissions } = useUserPermissions();
  const canView = allowPermissions(
    [EUserPermissions.ADMIN, EUserPermissions.MEMBER],
    EUserPermissionsLevel.PROJECT,
    workspaceSlug,
    projectId
  );
  const data = issueCostStore.reports[`${projectId}:${month}`];

  useEffect(() => {
    if (canView) void issueCostStore.fetchProjectReport(workspaceSlug, projectId, month);
  }, [canView, month, projectId, workspaceSlug]);

  if (!canView) return null;

  return (
    <section className="border-t border-subtle pt-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-heading-md font-medium text-primary">{t("issue.cost.report_title")}</h2>
        <input
          type="month"
          value={month || currentMonth()}
          onChange={(event) => onMonthChange(event.target.value)}
          className="h-8 rounded border border-subtle bg-surface-1 px-2 text-body-sm-regular text-primary"
        />
      </div>
      {!data ? (
        <div className="flex h-24 items-center justify-center">
          <Spinner />
        </div>
      ) : (
        <>
          <div className="mb-5 grid grid-cols-2 gap-x-6 gap-y-3 border-y border-subtle py-4 md:grid-cols-6">
            {[
              [t("issue.cost.estimated_total"), data.summary.estimated_person_days],
              [t("issue.cost.monthly_actual"), data.summary.monthly_actual_person_days],
              [t("issue.cost.actual_total"), data.summary.actual_person_days],
              [t("issue.cost.variance"), data.summary.variance_person_days],
              [t("issue.cost.missing_estimate"), data.summary.missing_estimate_count],
              [t("issue.cost.pending_actual"), data.summary.pending_actual_count],
            ].map(([label, value]) => (
              <div key={String(label)} className="min-w-0">
                <div className="truncate text-caption-sm-regular text-secondary">{label}</div>
                <div className="text-heading-lg mt-1 font-medium text-primary">{value}</div>
              </div>
            ))}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] border-collapse text-left text-body-sm-regular">
              <thead className="border-b border-subtle text-caption-sm-medium text-secondary">
                <tr>
                  <th className="px-2 py-2">{t("issue.label", { count: 1 })}</th>
                  <th className="px-2 py-2">{t("issue.cost.estimate")}</th>
                  <th className="px-2 py-2">{t("issue.cost.monthly_actual")}</th>
                  <th className="px-2 py-2">{t("issue.cost.actual_total")}</th>
                  <th className="px-2 py-2">{t("issue.cost.variance")}</th>
                  <th className="px-2 py-2">{t("issue.cost.pending_actual")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-subtle">
                {data.issues.map((item) => (
                  <tr key={item.issue_id}>
                    <td className="px-2 py-2 text-primary">
                      #{item.sequence_id} {item.name}
                    </td>
                    <td className="px-2 py-2">{item.estimated_person_days ?? "-"}</td>
                    <td className="px-2 py-2">{item.monthly_actual_person_days}</td>
                    <td className="px-2 py-2">{item.actual_person_days}</td>
                    <td className="px-2 py-2">{item.variance_person_days ?? "-"}</td>
                    <td className="px-2 py-2">{item.pending_actual_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
});
