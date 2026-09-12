import pytest
from django.urls import reverse
from rest_framework import status

from plane.db.models import Project, ProjectMember, ProjectUserProperty


@pytest.mark.contract
@pytest.mark.django_db
class TestProjectUserPropertyEndpoint:
    def test_group_by_null_remains_saved(self, session_client, create_user, workspace):
        project = Project.objects.create(
            name="Project user property test",
            identifier="PUP",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        project_user_property = ProjectUserProperty.objects.get(project=project, user=create_user)
        display_filters = {**project_user_property.display_filters, "group_by": None}
        url = reverse(
            "project-issue-display-properties",
            kwargs={"slug": workspace.slug, "project_id": project.id},
        )

        patch_response = session_client.patch(url, {"display_filters": display_filters}, format="json")

        assert patch_response.status_code == status.HTTP_200_OK
        assert patch_response.data["display_filters"]["group_by"] is None

        get_response = session_client.get(url)

        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.data["display_filters"]["group_by"] is None
        project_user_property.refresh_from_db()
        assert project_user_property.display_filters["group_by"] is None
