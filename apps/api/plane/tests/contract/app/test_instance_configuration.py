# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import uuid

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from plane.license.models import Instance, InstanceAdmin, InstanceConfiguration


@pytest.fixture
def default_workspace_configuration(db):
    return InstanceConfiguration.objects.create(
        key="DEFAULT_WORKSPACE_SLUG",
        value="",
        category="WORKSPACE_MANAGEMENT",
    )


@pytest.fixture
def configured_instance(db):
    return Instance.objects.create(
        instance_name="Test Instance",
        instance_id=str(uuid.uuid4()),
        current_version="1.0.0",
        domain="http://localhost:8000",
        last_checked_at=timezone.now(),
        is_setup_done=True,
    )


@pytest.fixture
def instance_admin_client(api_client, create_user, configured_instance):
    InstanceAdmin.objects.create(instance=configured_instance, user=create_user)
    api_client.force_authenticate(user=create_user)
    return api_client


@pytest.mark.contract
@pytest.mark.django_db
def test_instance_admin_can_set_default_workspace(instance_admin_client, default_workspace_configuration, workspace):
    response = instance_admin_client.patch(
        reverse("instance-configuration"),
        {"DEFAULT_WORKSPACE_SLUG": workspace.slug},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    default_workspace_configuration.refresh_from_db()
    assert default_workspace_configuration.value == workspace.slug


@pytest.mark.contract
@pytest.mark.django_db
def test_instance_admin_can_clear_default_workspace(instance_admin_client, default_workspace_configuration, workspace):
    default_workspace_configuration.value = workspace.slug
    default_workspace_configuration.save(update_fields=["value"])

    response = instance_admin_client.patch(
        reverse("instance-configuration"),
        {"DEFAULT_WORKSPACE_SLUG": ""},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    default_workspace_configuration.refresh_from_db()
    assert default_workspace_configuration.value == ""


@pytest.mark.contract
@pytest.mark.django_db
def test_invalid_default_workspace_is_rejected(instance_admin_client, default_workspace_configuration, workspace):
    default_workspace_configuration.value = workspace.slug
    default_workspace_configuration.save(update_fields=["value"])

    response = instance_admin_client.patch(
        reverse("instance-configuration"),
        {"DEFAULT_WORKSPACE_SLUG": "missing-workspace"},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json() == {"error": "Default workspace does not exist"}
    default_workspace_configuration.refresh_from_db()
    assert default_workspace_configuration.value == workspace.slug


@pytest.mark.contract
@pytest.mark.django_db
def test_non_instance_admin_cannot_set_default_workspace(
    session_client,
    configured_instance,
    default_workspace_configuration,
    workspace,
):
    response = session_client.patch(
        reverse("instance-configuration"),
        {"DEFAULT_WORKSPACE_SLUG": workspace.slug},
        format="json",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    default_workspace_configuration.refresh_from_db()
    assert default_workspace_configuration.value == ""
