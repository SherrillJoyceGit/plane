/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { useState } from "react";
import { observer } from "mobx-react";
import Link from "next/link";
import useSWR from "swr";
import { Loader as LoaderIcon } from "lucide-react";
// types
import { Button, getButtonStyling } from "@plane/propel/button";
import { setPromiseToast } from "@plane/propel/toast";
import type { TInstanceConfigurationKeys } from "@plane/types";
import { CustomSelect, Loader, ToggleSwitch } from "@plane/ui";
import { cn } from "@plane/utils";
// components
import { PageWrapper } from "@/components/common/page-wrapper";
import { WorkspaceListItem } from "@/components/workspace/list-item";
// hooks
import { useInstance, useWorkspace } from "@/hooks/store";
// types
import type { Route } from "./+types/page";

const WorkspaceManagementPage = observer(function WorkspaceManagementPage(_props: Route.ComponentProps) {
  // states
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  // store
  const { formattedConfig, fetchInstanceConfigurations, updateInstanceConfigurations } = useInstance();
  const {
    workspaceIds,
    loader: workspaceLoader,
    paginationInfo,
    fetchWorkspaces,
    fetchNextWorkspaces,
    getWorkspaceById,
  } = useWorkspace();
  // derived values
  const disableWorkspaceCreation = formattedConfig?.DISABLE_WORKSPACE_CREATION ?? "";
  const defaultWorkspaceSlug = formattedConfig?.DEFAULT_WORKSPACE_SLUG ?? "";
  const workspaceOptions = workspaceIds.flatMap((workspaceId) => {
    const workspace = getWorkspaceById(workspaceId);
    return workspace ? [workspace] : [];
  });
  const defaultWorkspace = workspaceOptions.find((workspace) => workspace.slug === defaultWorkspaceSlug);
  const defaultWorkspaceLabel = defaultWorkspace
    ? `${defaultWorkspace.name} [${defaultWorkspace.slug}]`
    : defaultWorkspaceSlug
      ? `Unavailable workspace [${defaultWorkspaceSlug}]`
      : "No default workspace";
  const hasMultipleWorkspaces = (paginationInfo?.total_results ?? workspaceIds.length) > 1;
  const hasNextPage = paginationInfo?.next_page_results && paginationInfo?.next_cursor !== undefined;

  // fetch data
  useSWR("INSTANCE_CONFIGURATIONS", () => fetchInstanceConfigurations());
  useSWR("INSTANCE_WORKSPACES", () => fetchWorkspaces());

  const updateConfig = async (key: TInstanceConfigurationKeys, value: string) => {
    setIsSubmitting(true);

    const payload = {
      [key]: value,
    };

    const updateConfigPromise = updateInstanceConfigurations(payload);

    setPromiseToast(updateConfigPromise, {
      loading: "Saving configuration",
      success: {
        title: "Success",
        message: () => "Configuration saved successfully",
      },
      error: {
        title: "Error",
        message: () => "Failed to save configuration",
      },
    });

    try {
      await updateConfigPromise;
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageWrapper
      header={{
        title: "Workspaces on this instance",
        description: "See all workspaces and control who can create them.",
      }}
    >
      <div className="space-y-3">
        {formattedConfig ? (
          <div className="space-y-6">
            <div className={cn("flex w-full items-center gap-14 rounded-sm")}>
              <div className="flex grow items-center gap-4">
                <div className="grow">
                  <div className="pb-1 text-16 font-medium">Prevent anyone else from creating a workspace.</div>
                  <div className={cn("text-11 leading-5 font-regular text-tertiary")}>
                    Toggling this on will let only you create workspaces. You will have to invite users to new
                    workspaces.
                  </div>
                </div>
              </div>
              <div className={`shrink-0 pr-4 ${isSubmitting && "opacity-70"}`}>
                <div className="flex items-center gap-4">
                  <ToggleSwitch
                    value={Boolean(parseInt(disableWorkspaceCreation))}
                    onChange={() => {
                      if (Boolean(parseInt(disableWorkspaceCreation)) === true) {
                        updateConfig("DISABLE_WORKSPACE_CREATION", "0");
                      } else {
                        updateConfig("DISABLE_WORKSPACE_CREATION", "1");
                      }
                    }}
                    size="sm"
                    disabled={isSubmitting}
                  />
                </div>
              </div>
            </div>
            <div className="flex w-full flex-col gap-3 rounded-sm sm:flex-row sm:items-start sm:gap-14">
              <div className="grow">
                <div className="pb-1 text-16 font-medium">Default workspace for new users</div>
                <div className="text-11 leading-5 font-regular text-tertiary">
                  New email and password sign-ups automatically join the selected workspace as Members.
                </div>
                {!defaultWorkspaceSlug && hasMultipleWorkspaces && (
                  <div className="pt-1 text-11 leading-5 font-regular text-warning-primary">
                    New users without an invitation will not join a workspace while no default is selected.
                  </div>
                )}
                {defaultWorkspaceSlug && !defaultWorkspace && (
                  <div className="pt-1 text-11 leading-5 font-regular text-danger-primary">
                    The configured workspace is unavailable or has not been loaded. Select an available workspace to
                    replace it.
                  </div>
                )}
              </div>
              <div className={`w-full shrink-0 sm:w-72 sm:pr-4 ${isSubmitting && "opacity-70"}`}>
                <CustomSelect
                  value={defaultWorkspaceSlug}
                  label={<span className="truncate">{defaultWorkspaceLabel}</span>}
                  onChange={(value: string) => updateConfig("DEFAULT_WORKSPACE_SLUG", value)}
                  buttonClassName="border-subtle"
                  className="w-full"
                  disabled={isSubmitting || workspaceLoader === "init-loader"}
                  input
                >
                  <CustomSelect.Option value="" className="w-full">
                    <span className="truncate">No default workspace</span>
                  </CustomSelect.Option>
                  {workspaceOptions.map((workspace) => (
                    <CustomSelect.Option key={workspace.id} value={workspace.slug} className="w-full">
                      <span className="truncate">
                        {workspace.name} [{workspace.slug}]
                      </span>
                    </CustomSelect.Option>
                  ))}
                </CustomSelect>
              </div>
            </div>
          </div>
        ) : (
          <Loader>
            <Loader.Item height="50px" width="100%" />
          </Loader>
        )}
        {workspaceLoader !== "init-loader" ? (
          <>
            <div className="flex items-center justify-between gap-2 pt-6">
              <div className="flex flex-col items-start gap-x-2">
                <div className="flex items-center gap-2 text-16 font-medium">
                  All workspaces on this instance <span className="text-tertiary">• {workspaceIds.length}</span>
                  {workspaceLoader && ["mutation", "pagination"].includes(workspaceLoader) && (
                    <LoaderIcon className="h-4 w-4 animate-spin" />
                  )}
                </div>
                <div className={cn("text-11 leading-5 font-regular text-tertiary")}>
                  You can&apos;t yet delete workspaces and you can only go to the workspace if you are an Admin or a
                  Member.
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Link href="/workspace/create" className={getButtonStyling("primary", "base")}>
                  Create workspace
                </Link>
              </div>
            </div>
            <div className="flex flex-col gap-4 py-2">
              {workspaceIds.map((workspaceId) => (
                <WorkspaceListItem key={workspaceId} workspaceId={workspaceId} />
              ))}
            </div>
            {hasNextPage && (
              <div className="flex justify-center">
                <Button
                  variant="link"
                  size="lg"
                  onClick={() => fetchNextWorkspaces()}
                  disabled={workspaceLoader === "pagination"}
                >
                  Load more
                  {workspaceLoader === "pagination" && <LoaderIcon className="h-3 w-3 animate-spin" />}
                </Button>
              </div>
            )}
          </>
        ) : (
          <Loader className="space-y-10 py-8">
            <Loader.Item height="24px" width="20%" />
            <Loader.Item height="92px" width="100%" />
            <Loader.Item height="92px" width="100%" />
            <Loader.Item height="92px" width="100%" />
          </Loader>
        )}
      </div>
    </PageWrapper>
  );
});

export const meta: Route.MetaFunction = () => [{ title: "Workspace Management - God Mode" }];

export default WorkspaceManagementPage;
