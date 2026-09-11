# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import serializers


class IssueTypeSerializer(serializers.Serializer):
    id = serializers.UUIDField(source="issue_type_id", read_only=True)
    name = serializers.CharField(source="issue_type.name", read_only=True)
    description = serializers.CharField(source="issue_type.description", read_only=True)
    logo_props = serializers.JSONField(source="issue_type.logo_props", read_only=True)
    is_default = serializers.BooleanField(read_only=True)
    is_active = serializers.BooleanField(source="issue_type.is_active", read_only=True)
    level = serializers.IntegerField(read_only=True)
