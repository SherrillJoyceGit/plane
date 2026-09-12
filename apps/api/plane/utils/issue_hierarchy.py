# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from plane.db.models import Issue, IssueWorklog


TOP_LEVEL_ISSUE_TYPES = frozenset({"Requirement", "Task", "Bug"})
PARENT_ISSUE_TYPES = frozenset({"Requirement", "Task"})
CHILD_ISSUE_TYPES = frozenset({"Task", "Bug"})


class IssueHierarchyError(Exception):
    def __init__(self, field, message):
        self.field = field
        self.message = message
        super().__init__(message)


def validate_issue_hierarchy(*, issue, project_id, parent, issue_type):
    """Validate the final parent/type combination for an issue create or update."""
    if issue_type is None or issue_type.name not in TOP_LEVEL_ISSUE_TYPES:
        raise IssueHierarchyError("type_id", "Only Requirement, Task, or Bug work item types are supported")

    has_children = bool(issue and Issue.issue_objects.filter(parent_id=issue.id).exists())

    if parent is None:
        if has_children and issue_type.name == "Bug":
            raise IssueHierarchyError("type_id", "A work item with children cannot be changed to Bug")
        return

    if parent.project_id != project_id:
        raise IssueHierarchyError("parent_id", "Parent work item must belong to the same project")
    if issue and parent.id == issue.id:
        raise IssueHierarchyError("parent_id", "A work item cannot be its own parent")
    if parent.parent_id is not None:
        raise IssueHierarchyError("parent_id", "Work items can have at most two levels")
    if parent.type is None or parent.type.name not in PARENT_ISSUE_TYPES:
        raise IssueHierarchyError("parent_id", "Only top-level Requirement or Task work items can have children")
    if IssueWorklog.objects.filter(issue=parent, deleted_at__isnull=True).exists():
        raise IssueHierarchyError("parent_id", "A work item with actual work cannot have children added")
    if issue_type.name not in CHILD_ISSUE_TYPES:
        raise IssueHierarchyError("type_id", "Child work items can only be Task or Bug")
    if has_children:
        raise IssueHierarchyError("parent_id", "A work item with children cannot become a child")
