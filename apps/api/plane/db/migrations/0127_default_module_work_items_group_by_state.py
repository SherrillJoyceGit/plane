from django.db import migrations


BATCH_SIZE = 2000


def default_module_work_items_group_by_state(apps, _schema_editor):
    ModuleUserProperties = apps.get_model("db", "ModuleUserProperties")
    properties_to_update = []

    for module_user_properties in ModuleUserProperties._base_manager.only("id", "display_filters").iterator(
        chunk_size=BATCH_SIZE
    ):
        display_filters = module_user_properties.display_filters
        if display_filters.get("group_by") is not None:
            continue

        module_user_properties.display_filters = {**display_filters, "group_by": "state"}
        properties_to_update.append(module_user_properties)

        if len(properties_to_update) >= BATCH_SIZE:
            ModuleUserProperties._base_manager.bulk_update(properties_to_update, ["display_filters"])
            properties_to_update.clear()

    if properties_to_update:
        ModuleUserProperties._base_manager.bulk_update(properties_to_update, ["display_filters"])


class Migration(migrations.Migration):
    dependencies = [("db", "0126_issue_rd_cost")]

    operations = [
        migrations.RunPython(default_module_work_items_group_by_state, migrations.RunPython.noop),
    ]
