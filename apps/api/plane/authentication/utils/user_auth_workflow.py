# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import logging
import os

from plane.db.models import Profile, Workspace, WorkspaceMember
from plane.license.utils.instance_value import get_configuration_value

from .workspace_project_join import process_workspace_project_invitations


logger = logging.getLogger("plane.authentication")


def join_default_workspace(user, request):
    (default_workspace_slug,) = get_configuration_value(
        [{"key": "DEFAULT_WORKSPACE_SLUG", "default": os.environ.get("DEFAULT_WORKSPACE_SLUG", "")}]
    )
    default_workspace_slug = str(default_workspace_slug).strip()

    if default_workspace_slug:
        workspace = Workspace.objects.filter(slug=default_workspace_slug).first()
        if workspace is None:
            logger.error("Configured default workspace does not exist", extra={"workspace_slug": default_workspace_slug})
            return
    elif request.POST.get("join_default_workspace") == "1" and Workspace.objects.count() == 1:
        workspace = Workspace.objects.first()
    else:
        return

    WorkspaceMember.objects.get_or_create(workspace=workspace, member=user, defaults={"role": 15})
    profile, _ = Profile.objects.get_or_create(user=user)
    profile.last_workspace_id = workspace.id
    profile.onboarding_step = {**profile.onboarding_step, "workspace_join": True}
    profile.save(update_fields=["last_workspace_id", "onboarding_step", "updated_at"])


def post_user_auth_workflow(user, is_signup, request):
    process_workspace_project_invitations(user=user)
    if is_signup and request.POST.get("password"):
        join_default_workspace(user=user, request=request)
