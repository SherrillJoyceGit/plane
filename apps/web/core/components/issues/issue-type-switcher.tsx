/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
// store hooks
import { useIssueDetail } from "@/hooks/store/use-issue-detail";
// components
import { IssueTypeDropdown } from "@/components/dropdowns/issue-type";
import { IssueIdentifier } from "@/components/issues/issue-detail/issue-identifier";

export type TIssueTypeSwitcherProps = {
  issueId: string;
  disabled: boolean;
};

export const IssueTypeSwitcher = observer(function IssueTypeSwitcher(props: TIssueTypeSwitcherProps) {
  const { issueId, disabled } = props;
  const { workspaceSlug } = useParams();
  // store hooks
  const {
    issue: { getIssueById },
    updateIssue,
  } = useIssueDetail();
  // derived values
  const issue = getIssueById(issueId);

  if (!issue || !issue.project_id) return <></>;
  const projectId = issue.project_id;

  return (
    <div className="flex items-center gap-2">
      <IssueIdentifier issueId={issueId} projectId={issue.project_id} size="md" enableClickToCopyIdentifier />
      <IssueTypeDropdown
        value={issue.type_id}
        projectId={projectId}
        disabled={disabled}
        hideText
        onChange={(typeId) => {
          if (workspaceSlug && typeId !== issue.type_id)
            void updateIssue(workspaceSlug.toString(), projectId, issueId, { type_id: typeId });
        }}
      />
    </div>
  );
});
