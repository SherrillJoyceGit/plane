/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { LucideIcon } from "lucide-react";
import { Bug, CircleDot, FileText, SquareCheckBig } from "lucide-react";
import { cn } from "@plane/utils";

const ISSUE_TYPE_ICONS: Record<string, LucideIcon> = {
  Requirement: FileText,
  Bug,
  Task: SquareCheckBig,
};

export type TIssueTypeIconProps = {
  className?: string;
  color?: string;
  typeName?: string;
};

export function IssueTypeIcon({ className, color, typeName }: TIssueTypeIconProps) {
  const Icon = ISSUE_TYPE_ICONS[typeName ?? ""] ?? CircleDot;
  return <Icon className={cn("size-4 flex-shrink-0", className)} style={color ? { color } : undefined} />;
}
