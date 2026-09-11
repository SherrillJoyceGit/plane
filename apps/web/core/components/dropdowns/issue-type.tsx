/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { observer } from "mobx-react";
import { useParams } from "next/navigation";
import { useTranslation } from "@plane/i18n";
import { CheckIcon, ChevronDownIcon } from "@plane/propel/icons";
import { getIssueTypeDisplayName } from "@plane/shared-state";
import { CustomMenu, IssueTypeIcon } from "@plane/ui";
import { cn } from "@plane/utils";
import { useIssueType } from "@/hooks/store/use-issue-type";

type Props = {
  value: string | null | undefined;
  onChange: (value: string) => void;
  projectId: string | null | undefined;
  disabled?: boolean;
  buttonClassName?: string;
  hideText?: boolean;
  tabIndex?: number;
};

export const IssueTypeDropdown = observer(function IssueTypeDropdown(props: Props) {
  const { value, onChange, projectId, disabled = false, buttonClassName, hideText = false, tabIndex } = props;
  const { workspaceSlug } = useParams();
  const { currentLocale } = useTranslation();
  const { getProjectIssueTypes, getIssueTypeById, fetchProjectIssueTypes } = useIssueType();
  const issueTypes = getProjectIssueTypes(projectId) ?? [];
  const selectedType = getIssueTypeById(value, projectId ?? undefined);
  const selectedName = getIssueTypeDisplayName(selectedType?.name ?? "Task", currentLocale);

  return (
    <CustomMenu
      ariaLabel="Work item type"
      customButton={
        <span
          className={cn(
            "flex h-7 items-center gap-1.5 rounded-sm border-[0.5px] border-strong px-2 py-0.5 text-body-xs-medium text-secondary hover:bg-layer-1",
            { "px-1.5": hideText },
            buttonClassName
          )}
        >
          <IssueTypeIcon typeName={selectedType?.name} color={selectedType?.logo_props.color} className="size-3.5" />
          {!hideText && <span className="max-w-32 truncate">{selectedName}</span>}
          {!hideText && <ChevronDownIcon className="size-3 flex-shrink-0" />}
        </span>
      }
      customButtonClassName="h-full"
      customButtonTabIndex={tabIndex}
      disabled={disabled || !projectId}
      menuButtonOnClick={() => {
        if (workspaceSlug && projectId) void fetchProjectIssueTypes(workspaceSlug.toString(), projectId);
      }}
      placement="bottom-start"
      closeOnSelect
    >
      {issueTypes.map((issueType) => (
        <CustomMenu.MenuItem key={issueType.id} onClick={() => onChange(issueType.id)}>
          <span className="flex items-center gap-2">
            <IssueTypeIcon typeName={issueType.name} color={issueType.logo_props.color} className="size-3.5" />
            <span className="flex-1">{getIssueTypeDisplayName(issueType.name, currentLocale)}</span>
            {value === issueType.id && <CheckIcon className="size-3.5" />}
          </span>
        </CustomMenu.MenuItem>
      ))}
    </CustomMenu>
  );
});
