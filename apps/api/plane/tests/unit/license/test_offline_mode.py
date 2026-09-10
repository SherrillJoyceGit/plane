# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
from unittest.mock import MagicMock, patch

import pytest

from plane.license.bgtasks.telemetry_metrics import push_instance_metrics
from plane.license.management.commands.register_instance import Command


@pytest.mark.unit
class TestOfflineMode:
    @patch.dict(os.environ, {"PLANE_OFFLINE_MODE": "1"})
    @patch("plane.license.management.commands.register_instance.requests.get")
    def test_latest_version_check_stays_local(self, mock_get):
        assert Command().check_for_latest_version("tc-plane-v0.0.1") == "tc-plane-v0.0.1"
        mock_get.assert_not_called()

    @patch.dict(os.environ, {"PLANE_OFFLINE_MODE": "1"})
    @patch("plane.license.management.commands.register_instance.push_instance_metrics.delay")
    @patch("plane.license.management.commands.register_instance.Instance.objects.first")
    def test_existing_instance_disables_telemetry(self, mock_first, mock_delay):
        instance = MagicMock()
        mock_first.return_value = instance

        Command().handle(machine_signature="test-machine")

        assert instance.is_telemetry_enabled is False
        mock_delay.assert_not_called()

    @patch.dict(os.environ, {"PLANE_OFFLINE_MODE": "1"})
    @patch("plane.license.bgtasks.telemetry_metrics._collect_and_push_metrics")
    def test_scheduled_telemetry_stays_local(self, mock_collect):
        push_instance_metrics()
        mock_collect.assert_not_called()
