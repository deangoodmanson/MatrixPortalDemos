"""Tests for text-to-speech module.

All tests mock subprocess and platform so nothing actually speaks.
"""

from unittest.mock import patch

from ledportal_pro.ui.tts import speak, speak_async


class TestSpeakMacOS:
    """On macOS, speak() calls 'say' with Zarvox."""

    @patch("ledportal_pro.ui.tts.platform.system", return_value="Darwin")
    @patch("ledportal_pro.ui.tts.subprocess.run")
    def test_calls_say_with_zarvox(self, mock_run, _mock_sys):
        speak("hello")
        mock_run.assert_called_once_with(["say", "-v", "Zarvox", "hello"], check=False)


class TestSpeakLinux:
    """On Linux, speak() calls espeak-ng with robotic settings."""

    @patch("ledportal_pro.ui.tts.platform.system", return_value="Linux")
    @patch("ledportal_pro.ui.tts.subprocess.run")
    def test_calls_espeak(self, mock_run, _mock_sys):
        speak("test prompt")
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "espeak-ng"
        assert "test prompt" in args


class TestSpeakWindows:
    """On Windows, speak() attempts pyttsx3."""

    @patch("ledportal_pro.ui.tts.platform.system", return_value="Windows")
    def test_no_crash_when_pyttsx3_missing(self, _mock_sys):
        # pyttsx3 is not installed in test env; should not raise
        speak("windows test")


class TestSpeakMissingTool:
    """If the TTS binary is missing, speak() silently continues."""

    @patch("ledportal_pro.ui.tts.platform.system", return_value="Darwin")
    @patch("ledportal_pro.ui.tts.subprocess.run", side_effect=FileNotFoundError)
    def test_file_not_found_is_silenced(self, _mock_run, _mock_sys):
        speak("should not raise")  # no exception

    @patch("ledportal_pro.ui.tts.platform.system", return_value="Linux")
    @patch("ledportal_pro.ui.tts.subprocess.run", side_effect=OSError("broken"))
    def test_os_error_is_silenced(self, _mock_run, _mock_sys):
        speak("should not raise")


class TestSpeakAsyncMacOS:
    """speak_async returns a Popen on macOS."""

    @patch("ledportal_pro.ui.tts.platform.system", return_value="Darwin")
    @patch("ledportal_pro.ui.tts.subprocess.Popen")
    def test_returns_popen(self, mock_popen, _mock_sys):
        mock_popen.return_value = "fake_process"
        result = speak_async("async hello")
        assert result == "fake_process"
        mock_popen.assert_called_once()
        assert mock_popen.call_args[0][0] == ["say", "-v", "Zarvox", "async hello"]

    @patch("ledportal_pro.ui.tts.platform.system", return_value="Windows")
    def test_returns_none_on_unsupported_platform(self, _mock_sys):
        """Windows has no Popen path in speak_async → returns None."""
        result = speak_async("no popen here")
        assert result is None
