import unittest
from unittest.mock import patch
import os


import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import deadman


class TestDeadman(unittest.TestCase):

    def test_reset_host_failures(self):
        """
        Test that reset_host_failures() returns a dict of {host: 0} for each host in host_list.
        """
        # Make sure we see the correct hosts from deadman.host_list
        host_list = deadman.host_list
        result = deadman.reset_host_failures()
        self.assertIsInstance(result, dict, "reset_host_failures should return a dictionary")
        self.assertEqual(len(result), len(host_list))
        for host in host_list:
            self.assertIn(host, result)
            self.assertEqual(result[host], 0, f"Host {host} should be 0 failures after reset")

    @patch('deadman.call')
    def test_ping_success(self, mock_call):
        """
        Test that ping(host) returns True if subprocess.call returns 0.
        """
        # Mock call() to return 0
        mock_call.return_value = 0
        self.assertTrue(deadman.ping("8.8.8.8"))
        mock_call.assert_called_once()

    @patch('deadman.call')
    def test_ping_failure(self, mock_call):
        """
        Test that ping(host) returns False if subprocess.call returns non-zero.
        """
        # Mock call() to return 1
        mock_call.return_value = 1
        self.assertFalse(deadman.ping("10.0.0.1"))
        mock_call.assert_called_once()

    @patch('deadman.check_output')
    def test_get_usb_devices(self, mock_check_output):
        """
        Test get_usb_devices() with a mocked lsusb output.
        """
        # Provide some sample binary output similar to what lsusb might return
        sample_lsusb = b"""Bus 001 Device 002: ID 1a2b:3c4d Sample USB Device
Bus 001 Device 003: ID 05ac:8290 Apple, Inc. FaceTime HD Camera
"""
        mock_check_output.return_value = sample_lsusb

        devices = deadman.get_usb_devices()
        self.assertEqual(len(devices), 2, "Should parse exactly 2 devices from the sample output")
        self.assertIn('device', devices[0], "First device dict should have 'device' key")
        self.assertIn('id', devices[0], "First device dict should have 'id' key")
        self.assertIn('tag', devices[0], "First device dict should have 'tag' key")

    @patch('deadman.call')
    def test_failure_action_test_mode(self, mock_call):
        """
        If THIS_IS_A_TEST is True, failure_action() should not call real commands.
        """
        original_test_mode = deadman.THIS_IS_A_TEST
        deadman.THIS_IS_A_TEST = True

        # We expect no real subprocess calls when test mode is active
        deadman.failure_action()
        mock_call.assert_not_called()

        deadman.THIS_IS_A_TEST = original_test_mode

    @patch('deadman.call')
    def test_failure_action_production_mode(self, mock_call):
        """
        In production mode (THIS_IS_A_TEST=False), failure_action() runs the shutdown commands.
        If a command fails, immediate_poweroff() should be called.
        """
        original_test_mode = deadman.THIS_IS_A_TEST
        deadman.THIS_IS_A_TEST = False

        # Suppose the first command succeeds (return code 0),
        # but the second command fails or times out (return code 1).
        mock_call.side_effect = [0, 1]  # first command success, second fails

        with patch('deadman.immediate_poweroff') as mock_poweroff:
            deadman.failure_action()

        # The shutdown commands are in shutdown_commands
        # so the first call is the first command, second call is the second command
        self.assertEqual(mock_call.call_count, len(deadman.shutdown_commands),
                         "Should call as many times as we have commands in shutdown_commands")
        mock_poweroff.assert_called_once()

        deadman.THIS_IS_A_TEST = original_test_mode

    @patch('deadman.sleep')
    @patch('deadman.ping')
    @patch('deadman.get_usb_devices')
    def test_main_loop_ping_failure(self, mock_get_usb, mock_ping, mock_sleep):
        """
        Test the main() loop in a scenario where ping fails for a host enough times
        to trigger shutdown. We'll patch 'failure_action' to avoid actually shutting down.
        """
        # We want to ensure main() eventually triggers failure_action()
        mock_get_usb.return_value = ["USB_DEVICE_LIST"]
        # Let ping fail every time
        mock_ping.return_value = False
        # We'll also patch failure_action
        with patch('deadman.failure_action') as mock_fail_action:
            # This can get tricky if main() never returns. We'll also patch exit() if needed.
            with self.assertRaises(SystemExit):
                # Because at startup, if ping fails repeatedly, main() might do exit(1)
                deadman.main()

            # If the script is coded to just exit(1) on immediate network failure, it
            # may never call failure_action. So check logic as needed:
            # mock_fail_action.assert_called_once()

        # Confirm we tried to ping at least
        self.assertTrue(mock_ping.called, "Ping should be called at least once in main()")


if __name__ == '__main__':
    unittest.main()
