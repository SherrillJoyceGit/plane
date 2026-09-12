from importlib import import_module

import pytest
from django.apps import apps

from plane.db.models import ProjectUserProperty
from plane.tests.factories import ProjectFactory, UserFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestProjectUserProperty:
    def test_defaults_to_state_grouping(self):
        project = ProjectFactory()
        project_user_property = ProjectUserProperty.objects.create(
            project=project,
            user=UserFactory(username="default-grouping-user"),
        )

        assert project_user_property.display_filters["group_by"] == "state"

    def test_migration_sets_only_missing_or_null_grouping(self):
        project = ProjectFactory()
        missing_group = ProjectUserProperty.objects.create(
            project=project,
            user=UserFactory(username="missing-group-user"),
            display_filters={"layout": "list", "order_by": "sort_order"},
        )
        null_group = ProjectUserProperty.objects.create(
            project=project,
            user=UserFactory(username="null-group-user"),
            display_filters={"layout": "list", "group_by": None, "show_empty_groups": False},
        )
        priority_group = ProjectUserProperty.objects.create(
            project=project,
            user=UserFactory(username="priority-group-user"),
            display_filters={"layout": "list", "group_by": "priority"},
        )

        migration = import_module("plane.db.migrations.0125_default_project_work_items_group_by_state")
        migration.default_project_work_items_group_by_state(apps, None)

        missing_group.refresh_from_db()
        null_group.refresh_from_db()
        priority_group.refresh_from_db()

        assert missing_group.display_filters == {
            "layout": "list",
            "order_by": "sort_order",
            "group_by": "state",
        }
        assert null_group.display_filters == {
            "layout": "list",
            "group_by": "state",
            "show_empty_groups": False,
        }
        assert priority_group.display_filters == {"layout": "list", "group_by": "priority"}
