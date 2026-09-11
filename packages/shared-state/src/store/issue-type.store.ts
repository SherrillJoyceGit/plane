/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { action, makeObservable, observable, runInAction } from "mobx";
import { computedFn } from "mobx-utils";
import type { TIssueType } from "@plane/types";

export type TIssueTypeFetcher = (workspaceSlug: string, projectId: string) => Promise<TIssueType[]>;

export interface IIssueTypeStore {
  projectIssueTypes: Record<string, TIssueType[]>;
  fetchedMap: Record<string, boolean>;
  loadingMap: Record<string, boolean>;
  getProjectIssueTypes: (projectId: string | null | undefined) => TIssueType[] | undefined;
  getIssueTypeById: (issueTypeId: string | null | undefined, projectId?: string) => TIssueType | undefined;
  getDefaultIssueTypeId: (projectId: string | null | undefined) => string | undefined;
  fetchProjectIssueTypes: (workspaceSlug: string, projectId: string) => Promise<TIssueType[]>;
}

const BUILT_IN_NAMES_ZH: Record<string, string> = {
  Requirement: "需求",
  Bug: "缺陷",
  Task: "任务",
};

export const getIssueTypeDisplayName = (name: string, locale: string): string =>
  locale === "zh-CN" || locale === "zh-TW" ? (BUILT_IN_NAMES_ZH[name] ?? name) : name;

export class IssueTypeStore implements IIssueTypeStore {
  projectIssueTypes: Record<string, TIssueType[]> = {};
  fetchedMap: Record<string, boolean> = {};
  loadingMap: Record<string, boolean> = {};
  private fetcher: TIssueTypeFetcher;
  private requests: Record<string, Promise<TIssueType[]> | undefined> = {};

  constructor(fetcher: TIssueTypeFetcher) {
    this.fetcher = fetcher;
    makeObservable(this, {
      projectIssueTypes: observable,
      fetchedMap: observable,
      loadingMap: observable,
      fetchProjectIssueTypes: action,
    });
  }

  getProjectIssueTypes = computedFn((projectId: string | null | undefined) => {
    if (!projectId || !this.fetchedMap[projectId]) return undefined;
    return this.projectIssueTypes[projectId] ?? [];
  });

  getIssueTypeById = computedFn((issueTypeId: string | null | undefined, projectId?: string) => {
    if (!issueTypeId) return undefined;
    if (projectId) return this.projectIssueTypes[projectId]?.find((issueType) => issueType.id === issueTypeId);
    return Object.values(this.projectIssueTypes)
      .flat()
      .find((issueType) => issueType.id === issueTypeId);
  });

  getDefaultIssueTypeId = computedFn(
    (projectId: string | null | undefined) =>
      this.getProjectIssueTypes(projectId)?.find((issueType) => issueType.is_default)?.id
  );

  fetchProjectIssueTypes = async (workspaceSlug: string, projectId: string) => {
    if (this.fetchedMap[projectId]) return this.projectIssueTypes[projectId] ?? [];
    if (this.requests[projectId]) return this.requests[projectId];

    runInAction(() => {
      this.loadingMap[projectId] = true;
    });
    const request = this.fetcher(workspaceSlug, projectId);
    this.requests[projectId] = request;

    try {
      const issueTypes = await request;
      runInAction(() => {
        this.projectIssueTypes[projectId] = issueTypes;
        this.fetchedMap[projectId] = true;
      });
      return issueTypes;
    } finally {
      runInAction(() => {
        this.loadingMap[projectId] = false;
      });
      delete this.requests[projectId];
    }
  };
}
