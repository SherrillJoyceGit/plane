from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from django.db import close_old_connections
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from plane.db.models import (
    DraftIssue,
    Issue,
    IssueActivity,
    IssueAssignee,
    IssueType,
    Project,
    ProjectMember,
    State,
    User,
    WorkspaceMember,
)


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Cost Project", identifier="COST", workspace=workspace, created_by=create_user
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.fixture
def states(db, workspace, project):
    return {
        group: State.objects.create(
            name=group.title(),
            group=group,
            default=group == "backlog",
            workspace=workspace,
            project=project,
        )
        for group in ("backlog", "started", "completed")
    }


def create_issue(workspace, project, states, name="Cost issue", type_name="Task", state_group="backlog", parent=None):
    return Issue.objects.create(
        name=name,
        workspace=workspace,
        project=project,
        state=states[state_group],
        type=IssueType.objects.get(workspace=workspace, name=type_name),
        parent=parent,
    )


def assign(issue, user):
    return IssueAssignee.objects.create(issue=issue, assignee=user, project=issue.project, workspace=issue.workspace)


def cost_url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/cost/"


def worklogs_url(workspace, project, issue):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/worklogs/"


@pytest.mark.contract
@pytest.mark.django_db
class TestIssueCostAPI:
    @pytest.mark.parametrize("value", ["0", "-0.5", "0.2", "1.2"])
    def test_estimate_requires_positive_half_day_increment(self, session_client, workspace, project, states, value):
        issue = create_issue(workspace, project, states)
        response = session_client.patch(
            cost_url(workspace, project, issue), {"estimated_person_days": value}, format="json"
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_estimate_is_only_allowed_on_top_level_requirement_or_task(
        self, session_client, workspace, project, states
    ):
        bug = create_issue(workspace, project, states, type_name="Bug")
        parent = create_issue(workspace, project, states, name="Parent")
        child = create_issue(workspace, project, states, name="Child", parent=parent)

        for issue in (bug, child):
            response = session_client.patch(
                cost_url(workspace, project, issue), {"estimated_person_days": "1.0"}, format="json"
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_start_requires_and_locks_estimate(self, session_client, workspace, project, states):
        issue = create_issue(workspace, project, states)
        issue_url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"

        missing = session_client.patch(issue_url, {"state_id": str(states["started"].id)}, format="json")
        assert missing.status_code == status.HTTP_400_BAD_REQUEST

        estimated = session_client.patch(
            cost_url(workspace, project, issue), {"estimated_person_days": "2.0"}, format="json"
        )
        assert estimated.status_code == status.HTTP_200_OK, estimated.data
        started = session_client.patch(issue_url, {"state_id": str(states["started"].id)}, format="json")
        assert started.status_code == status.HTTP_204_NO_CONTENT
        issue.refresh_from_db()
        assert issue.estimate_locked_at is not None

        locked = session_client.patch(
            cost_url(workspace, project, issue), {"estimated_person_days": "2.5"}, format="json"
        )
        assert locked.status_code == status.HTTP_400_BAD_REQUEST

    def test_start_can_estimate_and_lock_in_one_patch(self, session_client, workspace, project, states):
        issue = create_issue(workspace, project, states)
        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/",
            {"estimated_person_days": "1.5", "state_id": str(states["started"].id)},
            format="json",
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        issue.refresh_from_db()
        assert issue.estimated_person_days == Decimal("1.5")
        assert issue.estimate_locked_at is not None
        activity = IssueActivity.objects.get(issue=issue, field="estimated_person_days")
        assert activity.actor_id is not None
        assert activity.actor_id == issue.updated_by_id
        assert activity.old_value is None
        assert activity.new_value == '"1.5"'

    def test_starting_child_locks_parent_estimate(self, session_client, workspace, project, states):
        parent = create_issue(workspace, project, states, name="Parent")
        parent.estimated_person_days = Decimal("2.0")
        parent.save(update_fields=["estimated_person_days"])
        child = create_issue(workspace, project, states, name="Child", parent=parent)

        response = session_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{child.id}/",
            {"state_id": str(states["started"].id)},
            format="json",
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT, response.data
        parent.refresh_from_db()
        assert parent.estimate_locked_at is not None

    def test_historical_completed_issue_can_be_estimated_once(self, session_client, workspace, project, states):
        issue = create_issue(workspace, project, states, state_group="completed")
        first = session_client.patch(
            cost_url(workspace, project, issue), {"estimated_person_days": "1.0"}, format="json"
        )
        assert first.status_code == status.HTTP_200_OK, first.data
        issue.refresh_from_db()
        assert issue.estimate_locked_at is not None
        second = session_client.patch(
            cost_url(workspace, project, issue), {"estimated_person_days": "1.5"}, format="json"
        )
        assert second.status_code == status.HTTP_400_BAD_REQUEST
        assert IssueActivity.objects.filter(issue=issue, field="estimated_person_days").exists()

    def test_create_in_active_state_uses_the_same_estimate_gate(self, session_client, workspace, project, states):
        task = IssueType.objects.get(workspace=workspace, name="Task")
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/"

        missing = session_client.post(
            url,
            {"name": "Missing estimate", "type_id": str(task.id), "state_id": str(states["started"].id)},
            format="json",
        )
        assert missing.status_code == status.HTTP_400_BAD_REQUEST

        created = session_client.post(
            url,
            {
                "name": "Estimated on create",
                "type_id": str(task.id),
                "state_id": str(states["started"].id),
                "estimated_person_days": "2.0",
            },
            format="json",
        )
        assert created.status_code == status.HTTP_201_CREATED, created.data
        issue = Issue.objects.get(project=project, name="Estimated on create")
        assert issue.estimate_locked_at is not None
        assert IssueActivity.objects.filter(
            issue=issue,
            field="estimated_person_days",
            verb="created",
            new_value='"2.0"',
        ).exists()

        completed = session_client.post(
            url,
            {
                "name": "Completed on create",
                "type_id": str(task.id),
                "state_id": str(states["completed"].id),
                "estimated_person_days": "2.0",
            },
            format="json",
        )
        assert completed.status_code == status.HTTP_409_CONFLICT
        assert completed.data["code"] == "ACTUAL_WORK_CONFIRMATION_REQUIRED"

    def test_draft_publish_carries_estimate(self, session_client, workspace, project, states):
        issue_type = IssueType.objects.get(workspace=workspace, name="Task")
        draft = DraftIssue.objects.create(
            name="Estimated draft",
            workspace=workspace,
            project=project,
            state=states["backlog"],
            type=issue_type,
            estimated_person_days=Decimal("1.5"),
        )

        response = session_client.post(
            f"/api/workspaces/{workspace.slug}/draft-to-issue/{draft.id}/",
            {
                "name": draft.name,
                "state_id": str(states["backlog"].id),
                "type_id": str(issue_type.id),
            },
            format="json",
        )

        assert response.status_code == status.HTTP_201_CREATED, response.data
        issue = Issue.objects.get(project=project, name=draft.name)
        assert issue.estimated_person_days == Decimal("1.5")

    def test_estimated_item_cannot_become_child_or_bug_without_clearing_estimate(
        self, session_client, workspace, project, states
    ):
        parent = create_issue(workspace, project, states, name="Parent")
        issue = create_issue(workspace, project, states, name="Estimated")
        issue.estimated_person_days = Decimal("1.0")
        issue.save(update_fields=["estimated_person_days"])
        issue_url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"

        rejected = session_client.patch(issue_url, {"parent_id": str(parent.id)}, format="json")
        assert rejected.status_code == status.HTTP_400_BAD_REQUEST

        accepted = session_client.patch(
            issue_url,
            {"parent_id": str(parent.id), "estimated_person_days": None},
            format="json",
        )
        assert accepted.status_code == status.HTTP_204_NO_CONTENT, accepted.data
        issue.refresh_from_db()
        assert issue.parent_id == parent.id
        assert issue.estimated_person_days is None

    def test_worklogs_follow_leaf_and_workspace_daily_limit(
        self, session_client, workspace, project, states, create_user
    ):
        parent = create_issue(workspace, project, states, name="Parent", state_group="started")
        parent.estimated_person_days = Decimal("3.0")
        parent.save(update_fields=["estimated_person_days"])
        child = create_issue(workspace, project, states, name="Child", state_group="started", parent=parent)
        other = create_issue(workspace, project, states, name="Other", state_group="started")
        assign(parent, create_user)
        assign(child, create_user)
        assign(other, create_user)
        payload = {
            "member_id": str(create_user.id),
            "work_date": timezone.localdate().isoformat(),
            "person_days": "0.5",
            "description": "Implementation",
        }

        assert session_client.post(worklogs_url(workspace, project, parent), payload, format="json").status_code == 400
        first = session_client.post(worklogs_url(workspace, project, child), payload, format="json")
        assert first.status_code == status.HTTP_201_CREATED, first.data
        second = session_client.post(worklogs_url(workspace, project, other), payload, format="json")
        assert second.status_code == status.HTTP_201_CREATED
        over = session_client.post(worklogs_url(workspace, project, other), payload, format="json")
        assert over.status_code == status.HTTP_400_BAD_REQUEST
        assert IssueActivity.objects.filter(issue=child, field="worklog", verb="created").exists()

    def test_top_level_with_actual_work_cannot_gain_children(
        self, session_client, workspace, project, states, create_user
    ):
        parent = create_issue(workspace, project, states, state_group="started")
        assign(parent, create_user)
        logged = session_client.post(
            worklogs_url(workspace, project, parent),
            {
                "member_id": str(create_user.id),
                "work_date": timezone.localdate().isoformat(),
                "person_days": "0.5",
            },
            format="json",
        )
        assert logged.status_code == status.HTTP_201_CREATED
        child = create_issue(workspace, project, states, name="Candidate")
        attached = session_client.patch(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{child.id}/",
            {"parent_id": str(parent.id)},
            format="json",
        )
        assert attached.status_code == status.HTTP_400_BAD_REQUEST
        child.refresh_from_db()
        assert child.parent_id is None

    def test_future_worklog_is_rejected(self, session_client, workspace, project, states, create_user):
        issue = create_issue(workspace, project, states, state_group="started")
        assign(issue, create_user)
        response = session_client.post(
            worklogs_url(workspace, project, issue),
            {
                "member_id": str(create_user.id),
                "work_date": (timezone.localdate() + timedelta(days=1)).isoformat(),
                "person_days": "0.5",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_worklog_update_delete_audit_and_confirmation_reset(
        self, session_client, workspace, project, states, create_user
    ):
        issue = create_issue(workspace, project, states, state_group="completed")
        assign(issue, create_user)
        issue.zero_actual_confirmed_at = timezone.now()
        issue.zero_actual_confirmed_by = create_user
        issue.save(update_fields=["zero_actual_confirmed_at", "zero_actual_confirmed_by"])
        created = session_client.post(
            worklogs_url(workspace, project, issue),
            {
                "member_id": str(create_user.id),
                "work_date": timezone.localdate().isoformat(),
                "person_days": "0.5",
                "description": "Initial",
            },
            format="json",
        )
        assert created.status_code == status.HTTP_201_CREATED, created.data
        issue.refresh_from_db()
        assert issue.zero_actual_confirmed_at is None

        detail_url = f"{worklogs_url(workspace, project, issue)}{created.data['id']}/"
        updated = session_client.patch(detail_url, {"person_days": "1.0", "description": "Corrected"}, format="json")
        assert updated.status_code == status.HTTP_200_OK, updated.data
        assert updated.data["updated_by"] == create_user.id
        deleted = session_client.delete(detail_url)
        assert deleted.status_code == status.HTTP_204_NO_CONTENT

        activities = list(IssueActivity.objects.filter(issue=issue, field="worklog").order_by("created_at"))
        assert [activity.verb for activity in activities] == ["created", "updated", "deleted"]
        assert '"description": "Initial"' in activities[1].old_value
        assert '"description": "Corrected"' in activities[1].new_value
        assert '"person_days": "1.0"' in activities[2].old_value

    def test_completion_requires_confirmation_and_reopen_clears_it(
        self, session_client, workspace, project, states, create_user
    ):
        issue = create_issue(workspace, project, states, state_group="started")
        issue.estimated_person_days = Decimal("1.0")
        issue.estimate_locked_at = timezone.now()
        issue.save(update_fields=["estimated_person_days", "estimate_locked_at"])
        assign(issue, create_user)
        issue_url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/"

        blocked = session_client.patch(issue_url, {"state_id": str(states["completed"].id)}, format="json")
        assert blocked.status_code == status.HTTP_409_CONFLICT
        assert blocked.data["code"] == "ACTUAL_WORK_CONFIRMATION_REQUIRED"

        confirmation = session_client.post(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/{issue.id}/actual-work-confirmation/",
            {"confirm_no_actual_work": True},
            format="json",
        )
        assert confirmation.status_code == status.HTTP_200_OK
        completed = session_client.patch(
            issue_url,
            {"state_id": str(states["completed"].id), "confirm_no_actual_work": True},
            format="json",
        )
        assert completed.status_code == status.HTTP_204_NO_CONTENT
        reopened = session_client.patch(issue_url, {"state_id": str(states["started"].id)}, format="json")
        assert reopened.status_code == status.HTTP_204_NO_CONTENT
        issue.refresh_from_db()
        assert issue.zero_actual_confirmed_at is None

    def test_guest_cannot_access_cost_data(self, workspace, project, states):
        issue = create_issue(workspace, project, states)
        guest = User.objects.create_user(email=f"guest-{uuid4()}@example.com", username=f"guest-{uuid4()}")
        WorkspaceMember.objects.create(workspace=workspace, member=guest, role=5)
        ProjectMember.objects.create(project=project, member=guest, role=5, is_active=True)
        client = APIClient()
        client.force_authenticate(guest)

        response = client.get(cost_url(workspace, project, issue))
        assert response.status_code == status.HTTP_403_FORBIDDEN

        draft = client.post(
            f"/api/workspaces/{workspace.slug}/draft-issues/",
            {
                "project_id": str(project.id),
                "name": "Guest draft",
                "type_id": str(IssueType.objects.get(workspace=workspace, name="Task").id),
                "estimated_person_days": "1.0",
            },
            format="json",
        )
        assert draft.status_code == status.HTTP_400_BAD_REQUEST
        assert "estimated_person_days" in draft.data

    def test_member_can_log_only_for_self_and_admin_can_log_for_assignee(self, workspace, project, states, create_user):
        member = User.objects.create_user(email=f"member-{uuid4()}@example.com", username=f"member-{uuid4()}")
        WorkspaceMember.objects.create(workspace=workspace, member=member, role=15)
        ProjectMember.objects.create(project=project, member=member, role=15, is_active=True)
        issue = create_issue(workspace, project, states, state_group="started")
        assign(issue, member)
        assign(issue, create_user)
        member_client = APIClient()
        member_client.force_authenticate(member)

        own = member_client.post(
            worklogs_url(workspace, project, issue),
            {
                "member_id": str(member.id),
                "work_date": (timezone.localdate() - timedelta(days=2)).isoformat(),
                "person_days": "0.5",
            },
            format="json",
        )
        assert own.status_code == status.HTTP_201_CREATED, own.data
        other = member_client.post(
            worklogs_url(workspace, project, issue),
            {
                "member_id": str(create_user.id),
                "work_date": (timezone.localdate() - timedelta(days=1)).isoformat(),
                "person_days": "0.5",
            },
            format="json",
        )
        assert other.status_code == status.HTTP_400_BAD_REQUEST

        admin_client = APIClient()
        admin_client.force_authenticate(create_user)
        delegated = admin_client.post(
            worklogs_url(workspace, project, issue),
            {
                "member_id": str(member.id),
                "work_date": timezone.localdate().isoformat(),
                "person_days": "0.5",
            },
            format="json",
        )
        assert delegated.status_code == status.HTTP_201_CREATED, delegated.data

        IssueAssignee.objects.filter(issue=issue, assignee=member).delete()
        own_url = f"{worklogs_url(workspace, project, issue)}{own.data['id']}/"
        assert member_client.delete(own_url).status_code == status.HTTP_403_FORBIDDEN
        corrected = admin_client.patch(own_url, {"description": "Admin correction"}, format="json")
        assert corrected.status_code == status.HTTP_200_OK, corrected.data
        assert admin_client.delete(own_url).status_code == status.HTTP_204_NO_CONTENT

    def test_month_report_aggregates_children_and_excludes_soft_deleted_logs(
        self, session_client, workspace, project, states, create_user
    ):
        root = create_issue(workspace, project, states, name="Root", state_group="started")
        root.estimated_person_days = Decimal("2.0")
        root.save(update_fields=["estimated_person_days"])
        child = create_issue(workspace, project, states, name="Child", state_group="started", parent=root)
        assign(child, create_user)
        payload = {
            "member_id": str(create_user.id),
            "work_date": timezone.localdate().isoformat(),
            "person_days": "0.5",
        }
        created = session_client.post(worklogs_url(workspace, project, child), payload, format="json")
        assert created.status_code == status.HTTP_201_CREATED

        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/cost-report/",
            {"month": timezone.localdate().strftime("%Y-%m")},
        )
        assert response.status_code == status.HTTP_200_OK
        detail = next(item for item in response.data["issues"] if item["issue_id"] == root.id)
        assert detail["monthly_actual_person_days"] == Decimal("0.5")
        assert detail["variance_person_days"] == Decimal("-1.5")

    def test_report_summary_includes_top_level_bug_actual_without_adding_bug_detail(
        self, session_client, workspace, project, states, create_user
    ):
        bug = create_issue(workspace, project, states, name="Standalone bug", type_name="Bug", state_group="started")
        assign(bug, create_user)
        created = session_client.post(
            worklogs_url(workspace, project, bug),
            {
                "member_id": str(create_user.id),
                "work_date": timezone.localdate().isoformat(),
                "person_days": "0.5",
            },
            format="json",
        )
        assert created.status_code == status.HTTP_201_CREATED, created.data

        response = session_client.get(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/cost-report/",
            {"month": timezone.localdate().strftime("%Y-%m")},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["summary"]["actual_person_days"] == Decimal("0.5")
        assert response.data["summary"]["monthly_actual_person_days"] == Decimal("0.5")
        assert all(item["issue_id"] != bug.id for item in response.data["issues"])

        bug.deleted_at = timezone.now()
        bug.save(update_fields=["deleted_at"])
        after_delete = session_client.get(
            f"/api/workspaces/{workspace.slug}/projects/{project.id}/cost-report/",
            {"month": timezone.localdate().strftime("%Y-%m")},
        )
        assert after_delete.data["summary"]["actual_person_days"] == Decimal("0")


@pytest.mark.contract
@pytest.mark.django_db
def test_public_api_admin_or_member_can_read_and_write_estimate(api_key_client, workspace, project, states):
    issue = create_issue(workspace, project, states)
    url = f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{issue.id}/"

    estimated = api_key_client.patch(url, {"estimated_person_days": "1.0"}, format="json")
    assert estimated.status_code == status.HTTP_200_OK, estimated.data
    assert estimated.data["estimated_person_days"] == "1.0"
    assert IssueActivity.objects.filter(
        issue=issue,
        field="estimated_person_days",
        old_value__isnull=True,
        new_value='"1.0"',
    ).exists()

    started = api_key_client.patch(url, {"state": str(states["started"].id)}, format="json")
    assert started.status_code == status.HTTP_200_OK, started.data
    assert started.data["estimated_person_days"] == "1.0"
    assert "estimate_locked_at" not in started.data
    issue.refresh_from_db()
    assert issue.estimated_person_days == Decimal("1.0")
    assert issue.estimate_locked_at is not None


@pytest.mark.contract
@pytest.mark.django_db
def test_public_api_guest_cannot_read_or_write_estimate(workspace, project, states):
    issue = create_issue(workspace, project, states)
    issue.estimated_person_days = Decimal("1.0")
    issue.save(update_fields=["estimated_person_days"])
    guest = User.objects.create_user(email=f"guest-{uuid4()}@example.com", username=f"guest-{uuid4()}")
    WorkspaceMember.objects.create(workspace=workspace, member=guest, role=5)
    ProjectMember.objects.create(project=project, member=guest, role=5, is_active=True)
    client = APIClient()
    client.force_authenticate(guest)

    response = client.get(f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{issue.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert "estimated_person_days" not in response.data
    updated = client.patch(
        f"/api/v1/workspaces/{workspace.slug}/projects/{project.id}/work-items/{issue.id}/",
        {"estimated_person_days": "2.0"},
        format="json",
    )
    assert updated.status_code == status.HTTP_403_FORBIDDEN
    issue.refresh_from_db()
    assert issue.estimated_person_days == Decimal("1.0")


@pytest.mark.contract
@pytest.mark.django_db(transaction=True)
def test_concurrent_worklogs_cannot_exceed_workspace_daily_limit(workspace, project, states, create_user):
    first_issue = create_issue(workspace, project, states, name="First", state_group="started")
    second_issue = create_issue(workspace, project, states, name="Second", state_group="started")
    assign(first_issue, create_user)
    assign(second_issue, create_user)
    barrier = Barrier(2)

    def post_worklog(issue):
        close_old_connections()
        client = APIClient()
        client.force_authenticate(create_user)
        barrier.wait()
        response = client.post(
            worklogs_url(workspace, project, issue),
            {
                "member_id": str(create_user.id),
                "work_date": timezone.localdate().isoformat(),
                "person_days": "1.0",
            },
            format="json",
        )
        close_old_connections()
        return response.status_code

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(post_worklog, (first_issue, second_issue)))

    assert sorted(results) == [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
