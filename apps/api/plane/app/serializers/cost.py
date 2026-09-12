# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers

from plane.db.models import IssueWorklog


class IssueCostUpdateSerializer(serializers.Serializer):
    estimated_person_days = serializers.DecimalField(max_digits=8, decimal_places=1, allow_null=True, required=True)


class IssueWorklogSerializer(serializers.ModelSerializer):
    member_id = serializers.UUIDField()

    class Meta:
        model = IssueWorklog
        fields = [
            "id",
            "member_id",
            "work_date",
            "person_days",
            "description",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "created_by", "updated_by"]


class ActualWorkConfirmationSerializer(serializers.Serializer):
    confirm_no_actual_work = serializers.BooleanField()

    def validate_confirm_no_actual_work(self, value):
        if not value:
            raise serializers.ValidationError("Confirmation is required")
        return value
