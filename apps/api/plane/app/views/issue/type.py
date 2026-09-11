# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework import status
from rest_framework.response import Response

from plane.app.permissions import ROLE, allow_permission
from plane.app.serializers import IssueTypeSerializer
from plane.db.models import ProjectIssueType

from .. import BaseViewSet


class IssueTypeViewSet(BaseViewSet):
    model = ProjectIssueType
    serializer_class = IssueTypeSerializer

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                workspace__slug=self.kwargs.get("slug"),
                project_id=self.kwargs.get("project_id"),
                issue_type__is_active=True,
            )
            .select_related("issue_type")
            .order_by("level", "issue_type__name")
        )

    @allow_permission([ROLE.ADMIN, ROLE.MEMBER, ROLE.GUEST])
    def list(self, request, slug, project_id):
        return Response(IssueTypeSerializer(self.get_queryset(), many=True).data, status=status.HTTP_200_OK)
