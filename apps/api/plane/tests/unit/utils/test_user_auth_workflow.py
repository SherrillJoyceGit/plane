# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from plane.authentication.utils.user_auth_workflow import join_default_workspace
from plane.db.models import Profile, User, Workspace, WorkspaceMember


@pytest.fixture
def signup_user(db):
    user = User.objects.create(email="new-user@plane.so", username="new-user")
    Profile.objects.create(user=user)
    return user


@pytest.fixture
def default_workspace(db, create_user):
    return Workspace.objects.create(name="Default Workspace", slug="default-workspace", owner=create_user)


@pytest.mark.django_db
def test_configured_workspace_is_joined_without_form_choice(signup_user, default_workspace):
    request = SimpleNamespace(POST={})

    with patch(
        "plane.authentication.utils.user_auth_workflow.get_configuration_value",
        return_value=(default_workspace.slug,),
    ):
        join_default_workspace(signup_user, request)

    membership = WorkspaceMember.objects.get(workspace=default_workspace, member=signup_user)
    profile = Profile.objects.get(user=signup_user)
    assert membership.role == 15
    assert profile.last_workspace_id == default_workspace.id
    assert profile.onboarding_step["workspace_join"] is True


@pytest.mark.django_db
def test_user_can_opt_in_when_only_one_workspace_exists(signup_user, default_workspace):
    request = SimpleNamespace(POST={"join_default_workspace": "1"})

    with patch("plane.authentication.utils.user_auth_workflow.get_configuration_value", return_value=("",)):
        join_default_workspace(signup_user, request)

    assert WorkspaceMember.objects.filter(workspace=default_workspace, member=signup_user, role=15).exists()


@pytest.mark.django_db
def test_user_is_not_joined_without_opt_in(signup_user, default_workspace):
    request = SimpleNamespace(POST={})

    with patch("plane.authentication.utils.user_auth_workflow.get_configuration_value", return_value=("",)):
        join_default_workspace(signup_user, request)

    assert not WorkspaceMember.objects.filter(member=signup_user).exists()


@pytest.mark.django_db
def test_opt_in_does_not_choose_when_multiple_workspaces_exist(signup_user, default_workspace, create_user):
    Workspace.objects.create(name="Other Workspace", slug="other-workspace", owner=create_user)
    request = SimpleNamespace(POST={"join_default_workspace": "1"})

    with patch("plane.authentication.utils.user_auth_workflow.get_configuration_value", return_value=("",)):
        join_default_workspace(signup_user, request)

    assert not WorkspaceMember.objects.filter(member=signup_user).exists()


@pytest.mark.django_db
def test_existing_invitation_role_is_not_overwritten(signup_user, default_workspace):
    WorkspaceMember.objects.create(workspace=default_workspace, member=signup_user, role=5)
    request = SimpleNamespace(POST={})

    with patch(
        "plane.authentication.utils.user_auth_workflow.get_configuration_value",
        return_value=(default_workspace.slug,),
    ):
        join_default_workspace(signup_user, request)

    assert WorkspaceMember.objects.get(workspace=default_workspace, member=signup_user).role == 5


@pytest.mark.django_db
def test_invalid_configured_workspace_does_not_grant_membership(signup_user, default_workspace, caplog):
    request = SimpleNamespace(POST={"join_default_workspace": "1"})

    with patch(
        "plane.authentication.utils.user_auth_workflow.get_configuration_value",
        return_value=("missing-workspace",),
    ):
        join_default_workspace(signup_user, request)

    assert not WorkspaceMember.objects.filter(member=signup_user).exists()
    assert "Configured default workspace does not exist" in caplog.text
