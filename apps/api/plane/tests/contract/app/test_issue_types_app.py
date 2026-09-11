import pytest
from rest_framework import status

from plane.db.models import IssueType, Project, ProjectMember, User, WorkspaceMember


@pytest.fixture
def project(db, workspace, create_user):
    project = Project.objects.create(
        name="Issue types",
        identifier="TYPE",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(project=project, member=create_user, role=20, is_active=True)
    return project


@pytest.mark.contract
@pytest.mark.django_db
@pytest.mark.parametrize("role", [20, 15, 5])
def test_project_members_can_list_issue_types(session_client, workspace, project, role):
    user = User.objects.create_user(email=f"role-{role}@example.com", username=f"role-{role}")
    WorkspaceMember.objects.create(workspace=workspace, member=user, role=role)
    ProjectMember.objects.create(project=project, member=user, role=role, is_active=True)
    session_client.force_authenticate(user=user)

    response = session_client.get(f"/api/workspaces/{workspace.slug}/projects/{project.id}/issue-types/")

    assert response.status_code == status.HTTP_200_OK
    assert [item["name"] for item in response.data] == ["Requirement", "Bug", "Task"]
    assert set(response.data[0]) == {
        "id",
        "name",
        "description",
        "logo_props",
        "is_default",
        "is_active",
        "level",
    }
    assert [item["name"] for item in response.data if item["is_default"]] == ["Task"]


@pytest.mark.contract
@pytest.mark.django_db
def test_non_member_cannot_list_issue_types(session_client, workspace, project):
    outsider = User.objects.create_user(email="outsider@example.com", username="outsider")
    session_client.force_authenticate(user=outsider)

    response = session_client.get(f"/api/workspaces/{workspace.slug}/projects/{project.id}/issue-types/")

    assert response.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


@pytest.mark.contract
@pytest.mark.django_db
def test_issue_create_and_list_responses_include_type_id(session_client, workspace, project):
    task = IssueType.objects.get(workspace=workspace, name="Task")
    create_response = session_client.post(
        f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/",
        {"name": "Typed response"},
        format="json",
    )

    assert create_response.status_code == status.HTTP_201_CREATED, create_response.data
    assert create_response.data["type_id"] == task.id

    list_response = session_client.get(
        f"/api/workspaces/{workspace.slug}/projects/{project.id}/issues/?issues={create_response.data['id']}"
    )
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.data["results"][0]["type_id"] == task.id
