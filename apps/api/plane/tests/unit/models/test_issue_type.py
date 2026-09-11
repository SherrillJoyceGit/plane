import importlib

import pytest
from django.apps import apps

from plane.app.serializers import DraftIssueCreateSerializer, IssueCreateSerializer
from plane.api.serializers import IssueSerializer as PublicIssueSerializer
from plane.db.models import DraftIssue, Issue, IssueType, Project, ProjectIssueType, State


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Issue types",
        identifier="TYPE",
        workspace=workspace,
        created_by=create_user,
    )
    State.objects.create(name="Todo", group="backlog", default=True, project=project, workspace=workspace)
    return project


@pytest.mark.unit
@pytest.mark.django_db
def test_projects_share_three_workspace_types_with_task_as_only_default(workspace, create_user):
    first = Project.objects.create(name="First", identifier="ONE", workspace=workspace, created_by=create_user)
    second = Project.objects.create(name="Second", identifier="TWO", workspace=workspace, created_by=create_user)

    issue_types = IssueType.objects.filter(workspace=workspace).order_by("level")
    assert list(issue_types.values_list("name", "level")) == [
        ("Requirement", 0.0),
        ("Bug", 1.0),
        ("Task", 2.0),
    ]
    assert issue_types.filter(is_default=True).get().name == "Task"

    for project in (first, second):
        links = ProjectIssueType.objects.filter(project=project).select_related("issue_type").order_by("level")
        assert list(links.values_list("issue_type__name", flat=True)) == ["Requirement", "Bug", "Task"]
        assert links.filter(is_default=True).get().issue_type.name == "Task"


@pytest.mark.unit
@pytest.mark.django_db
def test_seed_migration_backfills_null_types_and_preserves_existing_types(project, workspace):
    ProjectIssueType.objects.filter(project=project).delete()
    IssueType.objects.filter(workspace=workspace).delete()
    custom = IssueType.objects.create(workspace=workspace, name="Custom")
    null_issue = Issue.objects.create(name="Null issue", project=project, workspace=workspace, type=None)
    typed_issue = Issue.objects.create(name="Typed issue", project=project, workspace=workspace, type=custom)
    null_draft = DraftIssue.objects.create(name="Null draft", project=project, workspace=workspace, type=None)
    typed_draft = DraftIssue.objects.create(name="Typed draft", project=project, workspace=workspace, type=custom)
    workspace_draft = DraftIssue.objects.create(name="Workspace draft", project=None, workspace=workspace, type=None)

    migration = importlib.import_module("plane.db.migrations.0124_seed_default_issue_types")
    migration.seed_default_issue_types(apps, None)
    task = IssueType.objects.get(workspace=workspace, name="Task")

    for item in (null_issue, typed_issue, null_draft, typed_draft, workspace_draft):
        item.refresh_from_db()
    assert null_issue.type == task
    assert null_draft.type == task
    assert typed_issue.type == custom
    assert typed_draft.type == custom
    assert workspace_draft.type is None


@pytest.mark.unit
@pytest.mark.django_db
def test_internal_issue_serializer_defaults_validates_and_updates_type(project, workspace):
    state = State.objects.get(project=project, default=True)
    task = IssueType.objects.get(workspace=workspace, name="Task")
    bug = IssueType.objects.get(workspace=workspace, name="Bug")
    other = Project.objects.create(name="Other", identifier="OTHER", workspace=workspace)
    foreign_type = IssueType.objects.create(workspace=workspace, name="Foreign")
    ProjectIssueType.objects.create(project=other, issue_type=foreign_type)
    context = {"project_id": project.id, "workspace_id": workspace.id, "default_assignee_id": None}

    serializer = IssueCreateSerializer(data={"name": "Default", "state_id": state.id}, context=context)
    assert serializer.is_valid(), serializer.errors
    issue = serializer.save()
    assert issue.type == task
    assert serializer.data["type_id"] == task.id

    explicit = IssueCreateSerializer(
        data={"name": "Bug", "state_id": state.id, "type_id": bug.id}, context=context
    )
    assert explicit.is_valid(), explicit.errors
    assert explicit.save().type == bug

    invalid = IssueCreateSerializer(
        data={"name": "Invalid", "state_id": state.id, "type_id": foreign_type.id}, context=context
    )
    assert not invalid.is_valid()
    assert "type_id" in invalid.errors

    unchanged = IssueCreateSerializer(issue, data={"name": "Renamed"}, partial=True, context=context)
    assert unchanged.is_valid(), unchanged.errors
    assert unchanged.save().type == task

    updated = IssueCreateSerializer(issue, data={"type_id": bug.id}, partial=True, context=context)
    assert updated.is_valid(), updated.errors
    assert updated.save().type == bug


@pytest.mark.unit
@pytest.mark.django_db
def test_draft_and_public_serializers_apply_the_same_type_rules(project, workspace):
    state = State.objects.get(project=project, default=True)
    task = IssueType.objects.get(workspace=workspace, name="Task")
    bug = IssueType.objects.get(workspace=workspace, name="Bug")
    other = Project.objects.create(name="Other serializers", identifier="SER", workspace=workspace)
    foreign_type = IssueType.objects.create(workspace=workspace, name="Foreign serializer type")
    ProjectIssueType.objects.create(project=other, issue_type=foreign_type)
    context = {"project_id": project.id, "workspace_id": workspace.id, "default_assignee_id": None}

    draft = DraftIssueCreateSerializer(data={"name": "Draft"}, context=context)
    assert draft.is_valid(), draft.errors
    assert draft.save().type == task

    explicit_draft = DraftIssueCreateSerializer(data={"name": "Bug draft", "type_id": bug.id}, context=context)
    assert explicit_draft.is_valid(), explicit_draft.errors
    assert explicit_draft.save().type == bug

    invalid_draft = DraftIssueCreateSerializer(data={"name": "Invalid", "type_id": foreign_type.id}, context=context)
    assert not invalid_draft.is_valid()
    assert "type_id" in invalid_draft.errors

    workspace_draft = DraftIssueCreateSerializer(
        data={"name": "Workspace draft"}, context={"project_id": None, "workspace_id": workspace.id}
    )
    assert workspace_draft.is_valid(), workspace_draft.errors
    assert workspace_draft.save().type is None

    public = PublicIssueSerializer(
        data={"name": "Public", "state": state.id, "type_id": None}, context=context
    )
    assert public.is_valid(), public.errors
    issue = public.save()
    assert issue.type == task
    assert public.data["type_id"] == task.id

    update = PublicIssueSerializer(issue, data={"type_id": bug.id}, partial=True, context=context)
    assert update.is_valid(), update.errors
    assert update.save().type == bug

    invalid_public = PublicIssueSerializer(
        issue, data={"type_id": foreign_type.id}, partial=True, context=context
    )
    assert not invalid_public.is_valid()
    assert "type_id" in invalid_public.errors
