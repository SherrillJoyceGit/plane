import pytest
from rest_framework import status

from plane.db.models import Module, Project, ProjectMember


@pytest.mark.contract
@pytest.mark.django_db
class TestModuleUserPropertiesEndpoint:
    def test_defaults_to_state_grouping_and_preserves_explicit_grouping(
        self, session_client, create_user, workspace
    ):
        project = Project.objects.create(
            name="Module user properties test",
            identifier="MUP",
            workspace=workspace,
            created_by=create_user,
        )
        ProjectMember.objects.create(project=project, member=create_user, role=20)
        module = Module.objects.create(name="Module", project=project)
        url = f"/api/workspaces/{workspace.slug}/projects/{project.id}/modules/{module.id}/user-properties/"

        get_response = session_client.get(url)

        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.data["display_filters"]["group_by"] == "state"

        display_filters = {**get_response.data["display_filters"], "group_by": "priority"}
        patch_response = session_client.patch(url, {"display_filters": display_filters}, format="json")

        assert patch_response.status_code == status.HTTP_201_CREATED
        assert patch_response.data["display_filters"]["group_by"] == "priority"
