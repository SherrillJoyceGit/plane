from django.db import migrations


BATCH_SIZE = 2000


def default_project_work_items_group_by_state(apps, _schema_editor):
    ProjectUserProperty = apps.get_model("db", "ProjectUserProperty")
    properties_to_update = []

    for project_user_property in ProjectUserProperty._base_manager.only("id", "display_filters").iterator(
        chunk_size=BATCH_SIZE
    ):
        display_filters = project_user_property.display_filters
        if display_filters.get("group_by") is not None:
            continue

        project_user_property.display_filters = {**display_filters, "group_by": "state"}
        properties_to_update.append(project_user_property)

        if len(properties_to_update) >= BATCH_SIZE:
            ProjectUserProperty._base_manager.bulk_update(properties_to_update, ["display_filters"])
            properties_to_update.clear()

    if properties_to_update:
        ProjectUserProperty._base_manager.bulk_update(properties_to_update, ["display_filters"])


class Migration(migrations.Migration):
    dependencies = [("db", "0124_seed_default_issue_types")]

    operations = [
        migrations.RunPython(default_project_work_items_group_by_state, migrations.RunPython.noop),
    ]
