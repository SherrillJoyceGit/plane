# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver

# Module imports
from .project import Project, ProjectBaseModel
from .base import BaseModel


DEFAULT_ISSUE_TYPES = (
    {
        "name": "Requirement",
        "logo_props": {"icon": "FileText", "color": "#3B82F6"},
        "level": 0,
    },
    {
        "name": "Bug",
        "logo_props": {"icon": "Bug", "color": "#DC2626"},
        "level": 1,
    },
    {
        "name": "Task",
        "logo_props": {"icon": "SquareCheckBig", "color": "#16A34A"},
        "level": 2,
    },
)


class IssueType(BaseModel):
    workspace = models.ForeignKey("db.Workspace", related_name="issue_types", on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    logo_props = models.JSONField(default=dict)
    is_epic = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    level = models.FloatField(default=0)
    external_source = models.CharField(max_length=255, null=True, blank=True)
    external_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = "Issue Type"
        verbose_name_plural = "Issue Types"
        db_table = "issue_types"

    def __str__(self):
        return self.name


class ProjectIssueType(ProjectBaseModel):
    issue_type = models.ForeignKey("db.IssueType", related_name="project_issue_types", on_delete=models.CASCADE)
    level = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)

    class Meta:
        unique_together = ["project", "issue_type", "deleted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "issue_type"],
                condition=Q(deleted_at__isnull=True),
                name="project_issue_type_unique_project_issue_type_when_deleted_at_null",
            )
        ]
        verbose_name = "Project Issue Type"
        verbose_name_plural = "Project Issue Types"
        db_table = "project_issue_types"
        ordering = ("project", "issue_type")

    def __str__(self):
        return f"{self.project} - {self.issue_type}"

    @classmethod
    def initialize_for_project(cls, project):
        from .workspace import Workspace

        with transaction.atomic():
            Workspace.objects.select_for_update().get(pk=project.workspace_id)
            issue_types = []
            for definition in DEFAULT_ISSUE_TYPES:
                issue_type, _ = IssueType.objects.update_or_create(
                    workspace_id=project.workspace_id,
                    name=definition["name"],
                    defaults={
                        "logo_props": definition["logo_props"],
                        "is_active": True,
                        "is_default": definition["name"] == "Task",
                        "level": definition["level"],
                    },
                )
                issue_types.append(issue_type)
                cls.objects.update_or_create(
                    project=project,
                    issue_type=issue_type,
                    defaults={
                        "is_default": definition["name"] == "Task",
                        "level": definition["level"],
                    },
                )

            IssueType.objects.filter(workspace_id=project.workspace_id, is_default=True).exclude(
                name="Task"
            ).update(is_default=False)
            cls.objects.filter(project=project, is_default=True).exclude(issue_type__name="Task").update(
                is_default=False
            )
            return issue_types

    @classmethod
    def get_default_issue_type(cls, project_id):
        project_issue_type = (
            cls.objects.filter(project_id=project_id, is_default=True, issue_type__is_active=True)
            .select_related("issue_type")
            .first()
        )
        return project_issue_type.issue_type if project_issue_type else None

    @classmethod
    def is_valid_issue_type(cls, project_id, issue_type_id):
        return cls.objects.filter(
            project_id=project_id,
            issue_type_id=issue_type_id,
            issue_type__is_active=True,
        ).exists()


@receiver(post_save, sender=Project)
def create_default_project_issue_types(sender, instance, created, **kwargs):
    if created:
        ProjectIssueType.initialize_for_project(instance)
