from importlib import import_module

import pytest
from django.apps import apps

from plane.db.models import Module, ModuleUserProperties
from plane.tests.factories import ProjectFactory, UserFactory


@pytest.mark.unit
@pytest.mark.django_db
class TestModuleUserProperties:
    def test_defaults_to_state_grouping(self):
        project = ProjectFactory()
        module = Module.objects.create(name="Default grouping module", project=project)
        module_user_properties = ModuleUserProperties.objects.create(
            module=module,
            project=project,
            user=UserFactory(username="module-default-grouping-user"),
        )

        assert module_user_properties.display_filters["group_by"] == "state"

    def test_migration_sets_only_missing_or_null_grouping(self):
        project = ProjectFactory()
        module = Module.objects.create(name="Migration module", project=project)
        missing_group = ModuleUserProperties.objects.create(
            module=module,
            project=project,
            user=UserFactory(username="module-missing-group-user"),
            display_filters={"layout": "list", "order_by": "sort_order"},
        )
        null_group = ModuleUserProperties.objects.create(
            module=module,
            project=project,
            user=UserFactory(username="module-null-group-user"),
            display_filters={"layout": "list", "group_by": None, "show_empty_groups": False},
        )
        priority_group = ModuleUserProperties.objects.create(
            module=module,
            project=project,
            user=UserFactory(username="module-priority-group-user"),
            display_filters={"layout": "list", "group_by": "priority"},
        )

        migration = import_module("plane.db.migrations.0127_default_module_work_items_group_by_state")
        migration.default_module_work_items_group_by_state(apps, None)

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
