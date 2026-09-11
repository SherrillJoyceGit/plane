# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.db.models import Profile, User


@pytest.mark.unit
class TestUserModel:
    @pytest.mark.django_db
    def test_new_user_defaults(self):
        user = User.objects.create(email="new-user@example.com", username="new-user")
        profile = Profile.objects.create(user=user)

        assert user.user_timezone == "Asia/Shanghai"
        assert profile.language == "zh-CN"
