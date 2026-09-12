# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import calendar
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import (
    ActualWorkConfirmationSerializer,
    IssueCostUpdateSerializer,
    IssueWorklogSerializer,
)
from plane.db.models import Issue, IssueWorklog, Workspace
from plane.utils.issue_cost import (
    CostValidationError,
    get_cost_root,
    has_actual_work,
    is_actual_registration_position,
    is_current_assignee,
    is_project_admin,
    record_cost_activity,
    save_worklog,
    validate_estimate_change,
    validate_worklog_target,
    worklog_snapshot,
)

from .. import BaseAPIView


def cost_error(error):
    return Response({error.field: error.message}, status=status.HTTP_400_BAD_REQUEST)


def get_issue(slug, project_id, issue_id):
    return (
        Issue.issue_objects.select_related("type", "state", "parent", "parent__type")
        .filter(workspace__slug=slug, project_id=project_id, pk=issue_id)
        .first()
    )


def cost_payload(issue):
    root = get_cost_root(issue)
    children = []
    actual_issue_ids = [issue.id]
    if issue.parent_id is None:
        children = list(Issue.issue_objects.filter(parent=issue).values_list("id", flat=True))
        actual_issue_ids = children or [issue.id]
    actual = IssueWorklog.objects.filter(issue_id__in=actual_issue_ids, deleted_at__isnull=True).aggregate(
        total=Sum("person_days")
    )["total"] or Decimal("0")
    estimate = root.estimated_person_days
    return {
        "issue_id": issue.id,
        "cost_root_id": root.id,
        "estimated_person_days": estimate,
        "estimate_locked_at": root.estimate_locked_at,
        "actual_person_days": actual,
        "variance_person_days": actual - estimate if estimate is not None else None,
        "zero_actual_confirmed_at": issue.zero_actual_confirmed_at,
        "zero_actual_confirmed_by": issue.zero_actual_confirmed_by_id,
        "can_log_actual": issue.parent_id is not None or not children,
    }


class IssueCostEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id, issue_id):
        issue = get_issue(slug, project_id, issue_id)
        if issue is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(cost_payload(issue))

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def patch(self, request, slug, project_id, issue_id):
        serializer = IssueCostUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            issue = (
                Issue.issue_objects.select_for_update(of=("self",))
                .select_related("type", "state", "parent")
                .filter(workspace__slug=slug, project_id=project_id, pk=issue_id)
                .first()
            )
            if issue is None:
                return Response(status=status.HTTP_404_NOT_FOUND)
            try:
                value = validate_estimate_change(
                    issue=issue,
                    value=serializer.validated_data["estimated_person_days"],
                    parent=issue.parent,
                    issue_type=issue.type,
                )
            except CostValidationError as error:
                return cost_error(error)
            old_value = issue.estimated_person_days
            issue.estimated_person_days = value
            update_fields = ["estimated_person_days", "updated_at"]
            if (
                value is not None
                and issue.estimate_locked_at is None
                and issue.state
                and issue.state.group in ("started", "completed")
            ):
                issue.estimate_locked_at = timezone.now()
                update_fields.append("estimate_locked_at")
            issue.save(update_fields=update_fields)
            if old_value != value:
                record_cost_activity(
                    issue,
                    request.user.id,
                    "estimated_person_days",
                    str(old_value) if old_value is not None else None,
                    str(value) if value is not None else None,
                )
        issue.refresh_from_db()
        return Response(cost_payload(issue))


class IssueWorklogListEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id, issue_id):
        issue = get_issue(slug, project_id, issue_id)
        if issue is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        worklogs = IssueWorklog.objects.filter(issue=issue, deleted_at__isnull=True).order_by(
            "-work_date", "-created_at"
        )
        return Response(IssueWorklogSerializer(worklogs, many=True).data)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id, issue_id):
        issue = get_issue(slug, project_id, issue_id)
        if issue is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = IssueWorklogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            validate_worklog_target(issue)
            worklog = save_worklog(
                issue=issue,
                actor_id=request.user.id,
                member_id=serializer.validated_data["member_id"],
                work_date=serializer.validated_data["work_date"],
                person_days=serializer.validated_data["person_days"],
                description=serializer.validated_data.get("description", ""),
            )
        except CostValidationError as error:
            return cost_error(error)
        return Response(IssueWorklogSerializer(worklog).data, status=status.HTTP_201_CREATED)


class IssueWorklogDetailEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def patch(self, request, slug, project_id, issue_id, worklog_id):
        issue = get_issue(slug, project_id, issue_id)
        worklog = IssueWorklog.objects.filter(
            pk=worklog_id, issue_id=issue_id, project_id=project_id, deleted_at__isnull=True
        ).first()
        if issue is None or worklog is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not is_project_admin(request.user.id, project_id) and worklog.member_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = IssueWorklogSerializer(worklog, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            worklog = save_worklog(
                issue=issue,
                actor_id=request.user.id,
                member_id=serializer.validated_data.get("member_id", worklog.member_id),
                work_date=serializer.validated_data.get("work_date", worklog.work_date),
                person_days=serializer.validated_data.get("person_days", worklog.person_days),
                description=serializer.validated_data.get("description", worklog.description),
                worklog=worklog,
            )
        except CostValidationError as error:
            return cost_error(error)
        return Response(IssueWorklogSerializer(worklog).data)

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def delete(self, request, slug, project_id, issue_id, worklog_id):
        worklog = (
            IssueWorklog.objects.filter(
                pk=worklog_id, issue_id=issue_id, project_id=project_id, deleted_at__isnull=True
            )
            .select_related("issue")
            .first()
        )
        if worklog is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not is_project_admin(request.user.id, project_id) and (
            worklog.member_id != request.user.id or not is_current_assignee(request.user.id, issue_id)
        ):
            return Response(status=status.HTTP_403_FORBIDDEN)
        old_value = worklog_snapshot(worklog)
        worklog.deleted_at = timezone.now()
        worklog.save(update_fields=["deleted_at", "updated_at"])
        record_cost_activity(worklog.issue, request.user.id, "worklog", old_value, None, "deleted")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ActualWorkConfirmationEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def post(self, request, slug, project_id, issue_id):
        serializer = ActualWorkConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            issue = get_issue(slug, project_id, issue_id)
            if issue is None:
                return Response(status=status.HTTP_404_NOT_FOUND)
            if not is_project_admin(request.user.id, project_id) and not is_current_assignee(request.user.id, issue.id):
                return Response(status=status.HTTP_403_FORBIDDEN)
            if issue.state is None or issue.state.group not in ("started", "completed"):
                return Response(
                    {"error": "Only started or completed work items can be confirmed"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not is_actual_registration_position(issue):
                return Response({"error": "Confirm child work items individually"}, status=status.HTTP_400_BAD_REQUEST)
            Workspace.objects.select_for_update().get(pk=issue.workspace_id)
            if has_actual_work(issue):
                return Response({"error": "Actual work already exists"}, status=status.HTTP_400_BAD_REQUEST)
            issue.zero_actual_confirmed_at = timezone.now()
            issue.zero_actual_confirmed_by_id = request.user.id
            issue.save(update_fields=["zero_actual_confirmed_at", "zero_actual_confirmed_by", "updated_at"])
        return Response(
            {
                "zero_actual_confirmed_at": issue.zero_actual_confirmed_at,
                "zero_actual_confirmed_by": issue.zero_actual_confirmed_by_id,
            }
        )


class ProjectCostReportEndpoint(BaseAPIView):
    @allow_permission([ROLE.ADMIN, ROLE.MEMBER])
    def get(self, request, slug, project_id):
        month = request.query_params.get("month", timezone.localdate().strftime("%Y-%m"))
        try:
            year, month_number = (int(value) for value in month.split("-"))
            month_start = date(year, month_number, 1)
            month_end = date(year, month_number, calendar.monthrange(year, month_number)[1])
        except (TypeError, ValueError):
            return Response({"month": "Use YYYY-MM format"}, status=status.HTTP_400_BAD_REQUEST)

        roots = list(
            Issue.issue_objects.filter(
                project_id=project_id, workspace__slug=slug, parent__isnull=True, type__name__in=("Requirement", "Task")
            ).order_by("sequence_id")
        )
        project_issues = list(
            Issue.issue_objects.filter(project_id=project_id, workspace__slug=slug).select_related("state")
        )
        parent_ids = {item.parent_id for item in project_issues if item.parent_id}
        registration_positions = [item for item in project_issues if item.parent_id or item.id not in parent_ids]
        project_logs = IssueWorklog.objects.filter(
            project_id=project_id,
            workspace__slug=slug,
            issue__deleted_at__isnull=True,
            deleted_at__isnull=True,
        )
        details = []
        total_estimate = Decimal("0")
        total_actual = project_logs.aggregate(total=Sum("person_days"))["total"] or Decimal("0")
        monthly_actual = project_logs.filter(work_date__range=(month_start, month_end)).aggregate(
            total=Sum("person_days")
        )["total"] or Decimal("0")
        missing_estimates = 0
        pending_actual = sum(
            1
            for item in registration_positions
            if item.state
            and item.state.group == "completed"
            and not item.zero_actual_confirmed_at
            and not has_actual_work(item)
        )
        for root in roots:
            children = list(Issue.issue_objects.filter(parent=root))
            positions = children or [root]
            position_ids = [item.id for item in positions]
            cumulative = IssueWorklog.objects.filter(issue_id__in=position_ids, deleted_at__isnull=True).aggregate(
                total=Sum("person_days")
            )["total"] or Decimal("0")
            monthly = IssueWorklog.objects.filter(
                issue_id__in=position_ids,
                deleted_at__isnull=True,
                work_date__range=(month_start, month_end),
            ).aggregate(total=Sum("person_days"))["total"] or Decimal("0")
            estimate = root.estimated_person_days
            missing_estimates += int(estimate is None)
            pending = sum(
                1
                for item in positions
                if item.state
                and item.state.group == "completed"
                and not item.zero_actual_confirmed_at
                and not has_actual_work(item)
            )
            total_estimate += estimate or Decimal("0")
            details.append(
                {
                    "issue_id": root.id,
                    "name": root.name,
                    "sequence_id": root.sequence_id,
                    "estimated_person_days": estimate,
                    "monthly_actual_person_days": monthly,
                    "actual_person_days": cumulative,
                    "variance_person_days": cumulative - estimate if estimate is not None else None,
                    "pending_actual_count": pending,
                }
            )
        return Response(
            {
                "month": month,
                "summary": {
                    "estimated_person_days": total_estimate,
                    "monthly_actual_person_days": monthly_actual,
                    "actual_person_days": total_actual,
                    "variance_person_days": total_actual - total_estimate,
                    "missing_estimate_count": missing_estimates,
                    "pending_actual_count": pending_actual,
                },
                "issues": details,
            }
        )
