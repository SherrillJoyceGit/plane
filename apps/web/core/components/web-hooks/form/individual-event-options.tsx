/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import type { Control } from "react-hook-form";
import { Controller } from "react-hook-form";
import { useTranslation } from "@plane/i18n";
import type { IWebhook } from "@plane/types";
import { Checkbox } from "@plane/ui";

export const INDIVIDUAL_WEBHOOK_OPTIONS: {
  key: keyof IWebhook;
  label: string;
  description: string;
  labelKey?: string;
  descriptionKey?: string;
}[] = [
  {
    key: "project",
    label: "Projects",
    description: "Project created, updated, or deleted",
  },
  {
    key: "cycle",
    label: "Cycles",
    description: "Cycle created, updated, or deleted",
  },
  {
    key: "issue",
    label: "Work items",
    description: "",
    descriptionKey: "module.webhook.work_item_description",
  },
  {
    key: "module",
    label: "",
    description: "",
    labelKey: "module.webhook.label",
    descriptionKey: "module.webhook.description",
  },
  {
    key: "issue_comment",
    label: "Work item comments",
    description: "Comment posted, updated, or deleted",
  },
];

type Props = {
  control: Control<IWebhook, any>;
};

export function WebhookIndividualEventOptions({ control }: Props) {
  const { t } = useTranslation();
  return (
    <div className="grid grid-cols-1 gap-x-4 gap-y-8 px-6 lg:grid-cols-2">
      {INDIVIDUAL_WEBHOOK_OPTIONS.map((option) => (
        <Controller
          key={option.key}
          control={control}
          name={option.key}
          render={({ field: { onChange, value } }) => (
            <div>
              <div className="flex items-center gap-2">
                <Checkbox id={option.key} onChange={() => onChange(!value)} checked={value === true} />
                <label className="text-13" htmlFor={option.key}>
                  {option.labelKey ? t(option.labelKey) : option.label}
                </label>
              </div>
              <p className="mt-0.5 ml-6 text-11 text-tertiary">
                {option.descriptionKey ? t(option.descriptionKey) : option.description}
              </p>
            </div>
          )}
        />
      ))}
    </div>
  );
}
