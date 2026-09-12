/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export const TOP_LEVEL_ISSUE_TYPE_NAMES = ["Requirement", "Task", "Bug"] as const;
export const PARENT_ISSUE_TYPE_NAMES = ["Requirement", "Task"] as const;
export const CHILD_ISSUE_TYPE_NAMES = ["Task", "Bug"] as const;

export const getAllowedIssueTypeNames = (hasParent: boolean, hasChildren: boolean): readonly string[] => {
  if (hasParent) return CHILD_ISSUE_TYPE_NAMES;
  if (hasChildren) return PARENT_ISSUE_TYPE_NAMES;
  return TOP_LEVEL_ISSUE_TYPE_NAMES;
};

export const canIssueHaveChildren = (typeName: string | undefined, parentId: string | null): boolean =>
  !parentId && PARENT_ISSUE_TYPE_NAMES.some((name) => name === typeName);

export const canIssueSetParent = (
  typeName: string | undefined,
  parentId: string | null,
  subIssuesCount: number
): boolean => !!parentId || (subIssuesCount === 0 && CHILD_ISSUE_TYPE_NAMES.some((name) => name === typeName));
