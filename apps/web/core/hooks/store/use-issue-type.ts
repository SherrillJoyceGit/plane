/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useContext } from "react";
import type { IIssueTypeStore } from "@plane/shared-state";
import { StoreContext } from "@/lib/store-context";

export const useIssueType = (): IIssueTypeStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("useIssueType must be used within StoreProvider");
  return context.issueType;
};
