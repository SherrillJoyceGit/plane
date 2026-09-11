/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

export type TIssueTypeLogoProps = {
  icon?: string;
  color?: string;
};

export type TIssueType = {
  id: string;
  name: string;
  description: string;
  logo_props: TIssueTypeLogoProps;
  is_default: boolean;
  is_active: boolean;
  level: number;
};
