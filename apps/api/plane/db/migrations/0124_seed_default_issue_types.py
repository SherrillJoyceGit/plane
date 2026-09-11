from django.db import migrations


DEFAULT_ISSUE_TYPES = (
    ("Requirement", {"icon": "FileText", "color": "#3B82F6"}, 0),
    ("Bug", {"icon": "Bug", "color": "#DC2626"}, 1),
    ("Task", {"icon": "SquareCheckBig", "color": "#16A34A"}, 2),
)


def seed_default_issue_types(apps, schema_editor):
    Workspace = apps.get_model("db", "Workspace")
    Project = apps.get_model("db", "Project")
    IssueType = apps.get_model("db", "IssueType")
    ProjectIssueType = apps.get_model("db", "ProjectIssueType")
    Issue = apps.get_model("db", "Issue")
    DraftIssue = apps.get_model("db", "DraftIssue")

    for workspace in Workspace.objects.all().iterator():
        issue_types = {}
        for name, logo_props, level in DEFAULT_ISSUE_TYPES:
            issue_type, _ = IssueType.objects.update_or_create(
                workspace_id=workspace.id,
                name=name,
                defaults={
                    "logo_props": logo_props,
                    "is_active": True,
                    "is_default": name == "Task",
                    "level": level,
                },
            )
            issue_types[name] = issue_type

        IssueType.objects.filter(workspace_id=workspace.id, is_default=True).exclude(name="Task").update(
            is_default=False
        )
        task_type = issue_types["Task"]

        for project in Project.objects.filter(workspace_id=workspace.id).iterator():
            for name, _, level in DEFAULT_ISSUE_TYPES:
                ProjectIssueType.objects.update_or_create(
                    project_id=project.id,
                    issue_type_id=issue_types[name].id,
                    defaults={
                        "workspace_id": workspace.id,
                        "is_default": name == "Task",
                        "level": level,
                    },
                )

            ProjectIssueType.objects.filter(project_id=project.id, is_default=True).exclude(
                issue_type_id=task_type.id
            ).update(is_default=False)
            Issue.objects.filter(project_id=project.id, type_id__isnull=True).update(type_id=task_type.id)
            DraftIssue.objects.filter(project_id=project.id, type_id__isnull=True).update(type_id=task_type.id)


class Migration(migrations.Migration):
    dependencies = [("db", "0123_update_new_user_defaults")]

    operations = [
        migrations.RunPython(seed_default_issue_types, migrations.RunPython.noop),
    ]
