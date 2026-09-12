# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import APIException

from plane.db.models import Issue, IssueActivity, IssueAssignee, IssueWorklog, ProjectMember, Workspace


ACTIVE_STATE_GROUPS = frozenset({"started", "completed"})
ESTIMATABLE_TYPES = frozenset({"Requirement", "Task"})


class CostValidationError(Exception):
    def __init__(self, field, message):
        self.field = field
        self.message = message
        super().__init__(message)


class ActualWorkConfirmationRequired(APIException):
    status_code = 409
    default_code = "ACTUAL_WORK_CONFIRMATION_REQUIRED"

    def __init__(self):
        super().__init__(
            {
                "code": self.default_code,
                "detail": "Confirm that this work item produced no actual work before completing it",
            }
        )


def decimal_person_days(value):
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise CostValidationError("estimated_person_days", "Enter a valid number of person-days") from error
    if result <= 0 or result % Decimal("0.5") != 0:
        raise CostValidationError(
            "estimated_person_days", "Estimated person-days must be positive and in increments of 0.5"
        )
    return result


def validate_estimate_change(*, issue, value, parent, issue_type):
    value = decimal_person_days(value)
    if issue and issue.estimate_locked_at and value != issue.estimated_person_days:
        raise CostValidationError("estimated_person_days", "Estimated person-days are locked")
    if value is not None and (parent is not None or issue_type is None or issue_type.name not in ESTIMATABLE_TYPES):
        raise CostValidationError(
            "estimated_person_days", "Only top-level Requirement or Task work items can be estimated"
        )
    return value


def get_cost_root(issue):
    return issue.parent if issue.parent_id else issue


def has_actual_work(issue):
    return IssueWorklog.objects.filter(issue=issue, deleted_at__isnull=True).exists()


def is_actual_registration_position(issue):
    return bool(issue.parent_id or not Issue.issue_objects.filter(parent=issue).exists())


def validate_cost_state_transition(
    *,
    issue,
    final_state,
    parent=None,
    issue_type=None,
    estimated_person_days=None,
    confirm_no_actual_work=False,
):
    if final_state is None or final_state.group not in ACTIVE_STATE_GROUPS:
        return
    root = parent or issue
    root_type = root.type if parent else issue_type or getattr(root, "type", None)
    root_estimate = root.estimated_person_days if parent else estimated_person_days
    if root_type and root_type.name in ESTIMATABLE_TYPES and root_estimate is None:
        raise CostValidationError("estimated_person_days", "Estimate the top-level work item before starting work")
    if final_state.group == "completed" and (
        issue is None
        or (
            is_actual_registration_position(issue)
            and not has_actual_work(issue)
            and not (confirm_no_actual_work and issue.zero_actual_confirmed_at)
        )
    ):
        raise ActualWorkConfirmationRequired()


def apply_cost_state_transition(*, issue, previous_state_group):
    current_group = issue.state.group if issue.state else None
    root = get_cost_root(issue)
    if (
        current_group in ACTIVE_STATE_GROUPS
        and root.estimated_person_days is not None
        and root.estimate_locked_at is None
    ):
        root.estimate_locked_at = timezone.now()
        Issue.objects.filter(pk=root.pk).update(estimate_locked_at=root.estimate_locked_at)
    if previous_state_group == "completed" and current_group != "completed":
        issue.zero_actual_confirmed_at = None
        issue.zero_actual_confirmed_by_id = None
        Issue.objects.filter(pk=issue.pk).update(zero_actual_confirmed_at=None, zero_actual_confirmed_by=None)


def is_project_admin(user_id, project_id):
    return ProjectMember.objects.filter(project_id=project_id, member_id=user_id, role=20, is_active=True).exists()


def is_current_assignee(user_id, issue_id):
    return IssueAssignee.objects.filter(issue_id=issue_id, assignee_id=user_id, deleted_at__isnull=True).exists()


def record_cost_activity(issue, actor_id, field, old_value, new_value, verb="updated"):
    IssueActivity.objects.create(
        issue=issue,
        actor_id=actor_id,
        project=issue.project,
        workspace=issue.workspace,
        verb=verb,
        field=field,
        old_value=json.dumps(old_value, default=str) if old_value is not None else None,
        new_value=json.dumps(new_value, default=str) if new_value is not None else None,
        comment=f"{verb} {field}",
    )


def worklog_snapshot(worklog):
    return {
        "id": str(worklog.id),
        "member_id": str(worklog.member_id),
        "work_date": worklog.work_date.isoformat(),
        "person_days": str(worklog.person_days),
        "description": worklog.description,
    }


def validate_worklog_target(issue):
    if issue.state is None or issue.state.group not in ACTIVE_STATE_GROUPS:
        raise CostValidationError("issue_id", "Actual work can only be added to started or completed work items")
    if not is_actual_registration_position(issue):
        raise CostValidationError("issue_id", "Add actual work to child work items when children exist")


def save_worklog(*, issue, actor_id, member_id, work_date, person_days, description, worklog=None):
    if work_date > timezone.localdate():
        raise CostValidationError("work_date", "Work date cannot be in the future")
    person_days = Decimal(str(person_days))
    if person_days not in (Decimal("0.5"), Decimal("1.0")):
        raise CostValidationError("person_days", "Person-days must be 0.5 or 1.0")
    admin = is_project_admin(actor_id, issue.project_id)
    if (worklog is None or member_id != worklog.member_id) and not is_current_assignee(member_id, issue.id):
        raise CostValidationError("member_id", "The worklog member must be a current assignee")
    if not admin and (actor_id != member_id or not is_current_assignee(actor_id, issue.id)):
        raise CostValidationError("member_id", "You can only manage your own worklogs")

    with transaction.atomic():
        Workspace.objects.select_for_update().get(pk=issue.workspace_id)
        daily_logs = IssueWorklog.objects.filter(
            workspace_id=issue.workspace_id,
            member_id=member_id,
            work_date=work_date,
            deleted_at__isnull=True,
        )
        if worklog:
            daily_logs = daily_logs.exclude(pk=worklog.pk)
        used = daily_logs.aggregate(total=Sum("person_days"))["total"] or Decimal("0")
        if used + person_days > Decimal("1.0"):
            raise CostValidationError("person_days", "Daily work across the workspace cannot exceed 1.0 person-day")
        old_value = worklog_snapshot(worklog) if worklog else None
        if worklog is None:
            worklog = IssueWorklog(
                issue=issue,
                member_id=member_id,
                work_date=work_date,
                person_days=person_days,
                description=description,
                project=issue.project,
                workspace=issue.workspace,
            )
            worklog.save(created_by_id=actor_id)
            verb = "created"
        else:
            worklog.member_id = member_id
            worklog.work_date = work_date
            worklog.person_days = person_days
            worklog.description = description
            worklog.updated_by_id = actor_id
            worklog.save(disable_auto_set_user=True)
            verb = "updated"
        Issue.objects.filter(pk=issue.pk).update(zero_actual_confirmed_at=None, zero_actual_confirmed_by=None)
        record_cost_activity(issue, actor_id, "worklog", old_value, worklog_snapshot(worklog), verb)
    return worklog
