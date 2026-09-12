# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import Issue, Project, State
from plane.utils.issue_hierarchy import IssueHierarchyError, validate_issue_hierarchy


@pytest.fixture
def project(db, workspace, create_user):
    return Project.objects.create(
        name="Hierarchy Project",
        identifier="HIER",
        workspace=workspace,
        created_by=create_user,
    )


@pytest.fixture
def state(db, workspace, project):
    return State.objects.create(
        name="Backlog",
        group="backlog",
        default=True,
        workspace=workspace,
        project=project,
    )


def get_type(project, name):
    return project.project_projectissuetype.select_related("issue_type").get(issue_type__name=name).issue_type


def create_issue(project, state, name, type_name, parent=None):
    return Issue.objects.create(
        name=name,
        workspace=project.workspace,
        project=project,
        state=state,
        type=get_type(project, type_name),
        parent=parent,
    )


@pytest.mark.unit
@pytest.mark.django_db
class TestIssueHierarchy:
    @pytest.mark.parametrize(
        ("parent_type", "child_type"),
        [
            ("Requirement", "Task"),
            ("Requirement", "Bug"),
            ("Task", "Task"),
            ("Task", "Bug"),
        ],
    )
    def test_all_valid_parent_child_type_combinations(self, project, state, parent_type, child_type):
        parent = create_issue(project, state, "Parent", parent_type)

        validate_issue_hierarchy(
            issue=None,
            project_id=project.id,
            parent=parent,
            issue_type=get_type(project, child_type),
        )

    @pytest.mark.parametrize("type_name", ["Requirement", "Task", "Bug"])
    def test_all_standard_types_are_valid_at_top_level(self, project, state, type_name):
        validate_issue_hierarchy(
            issue=None,
            project_id=project.id,
            parent=None,
            issue_type=get_type(project, type_name),
        )

    def test_rejects_a_third_level(self, project, state):
        parent = create_issue(project, state, "Parent", "Requirement")
        child = create_issue(project, state, "Child", "Task", parent=parent)

        with pytest.raises(IssueHierarchyError, match="at most two levels"):
            validate_issue_hierarchy(
                issue=None,
                project_id=project.id,
                parent=child,
                issue_type=get_type(project, "Task"),
            )

    def test_rejects_self_reference(self, project, state):
        issue = create_issue(project, state, "Issue", "Task")

        with pytest.raises(IssueHierarchyError, match="own parent"):
            validate_issue_hierarchy(
                issue=issue,
                project_id=project.id,
                parent=issue,
                issue_type=issue.type,
            )

    def test_rejects_cross_project_parent(self, project, state, workspace, create_user):
        other_project = Project.objects.create(
            name="Other Project",
            identifier="OTHER",
            workspace=workspace,
            created_by=create_user,
        )
        parent = create_issue(project, state, "Parent", "Task")

        with pytest.raises(IssueHierarchyError, match="same project"):
            validate_issue_hierarchy(
                issue=None,
                project_id=other_project.id,
                parent=parent,
                issue_type=get_type(other_project, "Task"),
            )

    @pytest.mark.parametrize("parent_type", ["Bug"])
    def test_rejects_parent_type_that_cannot_have_children(self, project, state, parent_type):
        parent = create_issue(project, state, "Parent", parent_type)

        with pytest.raises(IssueHierarchyError, match="Requirement or Task"):
            validate_issue_hierarchy(
                issue=None,
                project_id=project.id,
                parent=parent,
                issue_type=get_type(project, "Task"),
            )

    def test_rejects_requirement_child(self, project, state):
        parent = create_issue(project, state, "Parent", "Task")

        with pytest.raises(IssueHierarchyError, match="only be Task or Bug"):
            validate_issue_hierarchy(
                issue=None,
                project_id=project.id,
                parent=parent,
                issue_type=get_type(project, "Requirement"),
            )

    def test_rejects_parent_demotion_when_it_has_children(self, project, state):
        issue = create_issue(project, state, "Issue", "Requirement")
        create_issue(project, state, "Child", "Task", parent=issue)
        new_parent = create_issue(project, state, "New Parent", "Task")

        with pytest.raises(IssueHierarchyError, match="cannot become a child"):
            validate_issue_hierarchy(
                issue=issue,
                project_id=project.id,
                parent=new_parent,
                issue_type=get_type(project, "Task"),
            )

    def test_rejects_bug_type_when_issue_has_children(self, project, state):
        issue = create_issue(project, state, "Issue", "Requirement")
        create_issue(project, state, "Child", "Task", parent=issue)

        with pytest.raises(IssueHierarchyError, match="cannot be changed to Bug"):
            validate_issue_hierarchy(
                issue=issue,
                project_id=project.id,
                parent=None,
                issue_type=get_type(project, "Bug"),
            )

    def test_allows_child_to_become_top_level_requirement_atomically(self, project, state):
        parent = create_issue(project, state, "Parent", "Task")
        child = create_issue(project, state, "Child", "Task", parent=parent)

        validate_issue_hierarchy(
            issue=child,
            project_id=project.id,
            parent=None,
            issue_type=get_type(project, "Requirement"),
        )
