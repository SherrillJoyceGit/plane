# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import Issue, IssueType, Project, ProjectMember, State


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Hierarchy Contract Project",
        identifier="HCP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def state(db, workspace, project):
    return State.objects.create(
        name="Backlog",
        group="backlog",
        default=True,
        workspace=workspace,
        project=project,
    )


def get_type(workspace, name):
    return IssueType.objects.get(workspace=workspace, name=name)


def create_issue(workspace, project, state, name, type_name, parent=None):
    return Issue.objects.create(
        name=name,
        workspace=workspace,
        project=project,
        state=state,
        type=get_type(workspace, type_name),
        parent=parent,
    )


@pytest.mark.contract
@pytest.mark.django_db
class TestIssueHierarchyAppAPI:
    def test_patch_rejects_third_level(self, session_client, workspace, project, state):
        root = create_issue(workspace, project, state, "Root", "Requirement")
        child = create_issue(workspace, project, state, "Child", "Task", parent=root)
        candidate = create_issue(workspace, project, state, "Candidate", "Bug")

        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{candidate.id}/",
            {"parent_id": str(child.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "parent_id" in response.data
        candidate.refresh_from_db()
        assert candidate.parent_id is None

    def test_child_can_be_promoted_and_changed_to_requirement_in_one_patch(
        self, session_client, workspace, project, state
    ):
        root = create_issue(workspace, project, state, "Root", "Task")
        child = create_issue(workspace, project, state, "Child", "Task", parent=root)
        requirement = get_type(workspace, "Requirement")

        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{child.id}/",
            {"parent_id": None, "type_id": str(requirement.id)},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        child.refresh_from_db()
        assert child.parent_id is None
        assert child.type_id == requirement.id

    def test_parent_search_returns_only_top_level_requirement_and_task(
        self, session_client, workspace, project, state
    ):
        requirement = create_issue(workspace, project, state, "Requirement", "Requirement")
        task = create_issue(workspace, project, state, "Task", "Task")
        create_issue(workspace, project, state, "Bug", "Bug")
        create_issue(workspace, project, state, "Child", "Task", parent=requirement)

        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/search-issues/",
            {"parent": "true", "workspace_search": "false"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert {str(item["id"]) for item in response.data} == {str(requirement.id), str(task.id)}
        assert all(item["type_id"] for item in response.data)

    def test_bulk_attach_is_atomic_when_one_child_is_invalid(
        self, session_client, workspace, project, state
    ):
        parent = create_issue(workspace, project, state, "Parent", "Requirement")
        valid_child = create_issue(workspace, project, state, "Valid", "Task")
        invalid_child = create_issue(workspace, project, state, "Invalid", "Requirement")

        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{parent.id}/sub-issues/",
            {"sub_issue_ids": [str(valid_child.id), str(invalid_child.id)]},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        valid_child.refresh_from_db()
        invalid_child.refresh_from_db()
        assert valid_child.parent_id is None
        assert invalid_child.parent_id is None


@pytest.mark.contract
@pytest.mark.django_db
def test_public_api_uses_same_hierarchy_validation(api_key_client, workspace, project, state):
    root = create_issue(workspace, project, state, "Root", "Requirement")
    child = create_issue(workspace, project, state, "Child", "Task", parent=root)
    candidate = create_issue(workspace, project, state, "Candidate", "Bug")

    response = api_key_client.patch(
        f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{candidate.id}/",
        {"parent": str(child.id)},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "parent_id" in response.data
    candidate.refresh_from_db()
    assert candidate.parent_id is None
