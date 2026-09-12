# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.utils import timezone

# Third Party imports
from rest_framework import serializers

# Module imports
from .base import BaseSerializer
from plane.db.models import (
    User,
    Issue,
    Label,
    State,
    DraftIssue,
    DraftIssueAssignee,
    DraftIssueLabel,
    DraftIssueCycle,
    DraftIssueModule,
    ProjectMember,
    EstimatePoint,
    IssueType,
    ProjectIssueType,
)
from plane.utils.content_validator import (
    validate_html_content,
    validate_binary_data,
)
from plane.utils.issue_hierarchy import IssueHierarchyError, validate_issue_hierarchy
from plane.utils.issue_cost import CostValidationError, validate_estimate_change
from plane.app.permissions import ROLE


class DraftIssueCreateSerializer(BaseSerializer):
    # ids
    state_id = serializers.PrimaryKeyRelatedField(
        source="state", queryset=State.objects.all(), required=False, allow_null=True
    )
    parent_id = serializers.PrimaryKeyRelatedField(
        source="parent", queryset=Issue.objects.all(), required=False, allow_null=True
    )
    type_id = serializers.PrimaryKeyRelatedField(
        source="type", queryset=IssueType.objects.all(), required=False, allow_null=True
    )
    label_ids = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Label.objects.all()),
        write_only=True,
        required=False,
    )
    assignee_ids = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=User.objects.all()),
        write_only=True,
        required=False,
    )

    class Meta:
        model = DraftIssue
        fields = "__all__"
        read_only_fields = [
            "workspace",
            "type",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        assignee_ids = self.initial_data.get("assignee_ids")
        data["assignee_ids"] = assignee_ids if assignee_ids else []
        label_ids = self.initial_data.get("label_ids")
        data["label_ids"] = label_ids if label_ids else []
        return data

    def validate(self, attrs):
        project_id = self.context.get("project_id")
        if project_id:
            if "type" in attrs and attrs["type"] is not None:
                if not ProjectIssueType.is_valid_issue_type(project_id, attrs["type"].id):
                    raise serializers.ValidationError({"type_id": "Type is not valid for this project"})
            elif "type" in attrs or self.instance is None:
                issue_type = ProjectIssueType.get_default_issue_type(project_id)
                if issue_type is None:
                    raise serializers.ValidationError({"type_id": "Default type is not configured for this project"})
                attrs["type"] = issue_type
        elif "type" in attrs and attrs["type"] is not None:
            raise serializers.ValidationError({"type_id": "Project is required to set a type"})

        if (
            attrs.get("start_date", None) is not None
            and attrs.get("target_date", None) is not None
            and attrs.get("start_date", None) > attrs.get("target_date", None)
        ):
            raise serializers.ValidationError("Start date cannot exceed target date")

        # Validate description content for security
        if "description_html" in attrs and attrs["description_html"]:
            is_valid, error_msg, sanitized_html = validate_html_content(attrs["description_html"])
            if not is_valid:
                raise serializers.ValidationError({"error": "html content is not valid"})
            # Update the attrs with sanitized HTML if available
            if sanitized_html is not None:
                attrs["description_html"] = sanitized_html

        if "description_binary" in attrs and attrs["description_binary"]:
            is_valid, error_msg = validate_binary_data(attrs["description_binary"])
            if not is_valid:
                raise serializers.ValidationError({"description_binary": "Invalid binary data"})

        # Validate assignees are from project
        if attrs.get("assignee_ids", []):
            attrs["assignee_ids"] = ProjectMember.objects.filter(
                project_id=self.context["project_id"],
                role__gte=ROLE.MEMBER.value,
                is_active=True,
                member_id__in=attrs["assignee_ids"],
            ).values_list("member_id", flat=True)

        # Validate labels are from project
        if attrs.get("label_ids"):
            label_ids = [label.id for label in attrs["label_ids"]]
            attrs["label_ids"] = list(
                Label.objects.filter(project_id=self.context.get("project_id"), id__in=label_ids).values_list(
                    "id", flat=True
                )
            )

        # # Check state is from the project only else raise validation error
        if (
            attrs.get("state")
            and not State.objects.filter(
                project_id=self.context.get("project_id"),
                pk=attrs.get("state").id,
            ).exists()
        ):
            raise serializers.ValidationError("State is not valid please pass a valid state_id")

        final_parent = attrs.get("parent", self.instance.parent if self.instance else None)
        final_type = attrs.get("type", self.instance.type if self.instance else None)
        if project_id or final_parent or final_type:
            try:
                validate_issue_hierarchy(
                    issue=None,
                    project_id=project_id,
                    parent=final_parent,
                    issue_type=final_type,
                )
            except IssueHierarchyError as error:
                raise serializers.ValidationError({error.field: error.message}) from error

        if "estimated_person_days" in attrs:
            if not ProjectMember.objects.filter(
                project_id=project_id,
                member_id=self.context.get("user_id"),
                role__gte=ROLE.MEMBER.value,
                is_active=True,
            ).exists():
                raise serializers.ValidationError({"estimated_person_days": "You cannot access cost data"})
            try:
                attrs["estimated_person_days"] = validate_estimate_change(
                    issue=None,
                    value=attrs["estimated_person_days"],
                    parent=final_parent,
                    issue_type=final_type,
                )
            except CostValidationError as error:
                raise serializers.ValidationError({error.field: error.message}) from error

        if (
            attrs.get("estimate_point")
            and not EstimatePoint.objects.filter(
                project_id=self.context.get("project_id"),
                pk=attrs.get("estimate_point").id,
            ).exists()
        ):
            raise serializers.ValidationError("Estimate point is not valid please pass a valid estimate_point_id")

        return attrs

    def create(self, validated_data):
        assignees = validated_data.pop("assignee_ids", None)
        labels = validated_data.pop("label_ids", None)
        modules = validated_data.pop("module_ids", None)
        cycle_id = self.initial_data.get("cycle_id", None)
        modules = self.initial_data.get("module_ids", None)

        workspace_id = self.context["workspace_id"]
        project_id = self.context["project_id"]

        # Create Issue
        issue = DraftIssue.objects.create(**validated_data, workspace_id=workspace_id, project_id=project_id)

        # Issue Audit Users
        created_by_id = issue.created_by_id
        updated_by_id = issue.updated_by_id

        if assignees is not None and len(assignees):
            DraftIssueAssignee.objects.bulk_create(
                [
                    DraftIssueAssignee(
                        assignee_id=assignee_id,
                        draft_issue=issue,
                        workspace_id=workspace_id,
                        project_id=project_id,
                        created_by_id=created_by_id,
                        updated_by_id=updated_by_id,
                    )
                    for assignee_id in assignees
                ],
                batch_size=10,
            )

        if labels is not None and len(labels):
            DraftIssueLabel.objects.bulk_create(
                [
                    DraftIssueLabel(
                        label_id=label_id,
                        draft_issue=issue,
                        project_id=project_id,
                        workspace_id=workspace_id,
                        created_by_id=created_by_id,
                        updated_by_id=updated_by_id,
                    )
                    for label_id in labels
                ],
                batch_size=10,
            )

        if cycle_id is not None:
            DraftIssueCycle.objects.create(
                cycle_id=cycle_id,
                draft_issue=issue,
                project_id=project_id,
                workspace_id=workspace_id,
                created_by_id=created_by_id,
                updated_by_id=updated_by_id,
            )

        if modules is not None and len(modules):
            DraftIssueModule.objects.bulk_create(
                [
                    DraftIssueModule(
                        module_id=module_id,
                        draft_issue=issue,
                        project_id=project_id,
                        workspace_id=workspace_id,
                        created_by_id=created_by_id,
                        updated_by_id=updated_by_id,
                    )
                    for module_id in modules
                ],
                batch_size=10,
            )

        return issue

    def update(self, instance, validated_data):
        assignees = validated_data.pop("assignee_ids", None)
        labels = validated_data.pop("label_ids", None)
        cycle_id = self.context.get("cycle_id", None)
        modules = self.initial_data.get("module_ids", None)

        # Related models
        workspace_id = instance.workspace_id
        project_id = instance.project_id

        created_by_id = instance.created_by_id
        updated_by_id = instance.updated_by_id

        if assignees is not None:
            DraftIssueAssignee.objects.filter(draft_issue=instance).delete()
            DraftIssueAssignee.objects.bulk_create(
                [
                    DraftIssueAssignee(
                        assignee_id=assignee_id,
                        draft_issue=instance,
                        workspace_id=workspace_id,
                        project_id=project_id,
                        created_by_id=created_by_id,
                        updated_by_id=updated_by_id,
                    )
                    for assignee_id in assignees
                ],
                batch_size=10,
            )

        if labels is not None:
            DraftIssueLabel.objects.filter(draft_issue=instance).delete()
            DraftIssueLabel.objects.bulk_create(
                [
                    DraftIssueLabel(
                        label_id=label,
                        draft_issue=instance,
                        workspace_id=workspace_id,
                        project_id=project_id,
                        created_by_id=created_by_id,
                        updated_by_id=updated_by_id,
                    )
                    for label in labels
                ],
                batch_size=10,
            )

        if cycle_id != "not_provided":
            DraftIssueCycle.objects.filter(draft_issue=instance).delete()
            if cycle_id:
                DraftIssueCycle.objects.create(
                    cycle_id=cycle_id,
                    draft_issue=instance,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    created_by_id=created_by_id,
                    updated_by_id=updated_by_id,
                )

        if modules is not None:
            DraftIssueModule.objects.filter(draft_issue=instance).delete()
            DraftIssueModule.objects.bulk_create(
                [
                    DraftIssueModule(
                        module_id=module_id,
                        draft_issue=instance,
                        workspace_id=workspace_id,
                        project_id=project_id,
                        created_by_id=created_by_id,
                        updated_by_id=updated_by_id,
                    )
                    for module_id in modules
                ],
                batch_size=10,
            )

        # Time updation occurs even when other related models are updated
        instance.updated_at = timezone.now()
        return super().update(instance, validated_data)


class DraftIssueSerializer(BaseSerializer):
    # ids
    cycle_id = serializers.PrimaryKeyRelatedField(read_only=True)
    module_ids = serializers.ListField(child=serializers.UUIDField(), required=False)

    # Many to many
    label_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    assignee_ids = serializers.ListField(child=serializers.UUIDField(), required=False)

    class Meta:
        model = DraftIssue
        fields = [
            "id",
            "name",
            "state_id",
            "sort_order",
            "completed_at",
            "estimate_point",
            "estimated_person_days",
            "priority",
            "start_date",
            "target_date",
            "project_id",
            "parent_id",
            "cycle_id",
            "module_ids",
            "label_ids",
            "assignee_ids",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "type_id",
            "description_html",
        ]
        read_only_fields = fields

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not ProjectMember.objects.filter(
            project_id=instance.project_id,
            member_id=self.context.get("user_id"),
            role__gte=ROLE.MEMBER.value,
            is_active=True,
        ).exists():
            data.pop("estimated_person_days", None)
        return data


class DraftIssueDetailSerializer(DraftIssueSerializer):
    description_html = serializers.CharField()

    class Meta(DraftIssueSerializer.Meta):
        fields = DraftIssueSerializer.Meta.fields + ["description_html"]
        read_only_fields = fields
