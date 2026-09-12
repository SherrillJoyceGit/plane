/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { IssueCostStore } from "@plane/shared-state";
import { IssueCostService } from "@/services/issue";

export const issueCostStore = new IssueCostStore(new IssueCostService());
