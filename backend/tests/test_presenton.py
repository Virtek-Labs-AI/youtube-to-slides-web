from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.services.presenton import _build_download_url, _poll_until_complete, generate_pptx


def _mock_response(json_data: Any, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    resp.content = b"PPTX_BYTES"
    return resp


class TestBuildDownloadUrl:
    def test_happy_path(self) -> None:
        url = _build_download_url("http://presenton:5000", "/app_data/exports/My Slides.pptx")
        assert url == "http://presenton:5000/app_data/exports/My%20Slides.pptx"

    def test_rejects_path_traversal(self) -> None:
        with pytest.raises(ValueError, match="invalid export path"):
            _build_download_url("http://presenton:5000", "/app_data/exports/../secret.pptx")

    def test_rejects_backslash(self) -> None:
        with pytest.raises(ValueError, match="invalid export path"):
            _build_download_url("http://presenton:5000", "/exports/bad\\file.pptx")

    def test_rejects_empty_filename(self) -> None:
        with pytest.raises(ValueError, match="invalid export path"):
            _build_download_url("http://presenton:5000", "/exports/")


class TestPollUntilComplete:
    def test_returns_data_on_completed(self) -> None:
        completed = {"status": "completed", "data": {"path": "/app_data/exports/slides.pptx"}}
        with patch("httpx.get", return_value=_mock_response(completed)):
            result = _poll_until_complete.__wrapped__("http://presenton:5000", "task-1")
        assert result == {"path": "/app_data/exports/slides.pptx"}

    def test_returns_none_when_pending(self) -> None:
        pending = {"status": "pending", "message": "Generating..."}
        with patch("httpx.get", return_value=_mock_response(pending)):
            result = _poll_until_complete.__wrapped__("http://presenton:5000", "task-1")
        assert result is None

    def test_raises_on_error_status(self) -> None:
        error = {"status": "error", "error": "LLM quota exceeded"}
        with patch("httpx.get", return_value=_mock_response(error)):
            with pytest.raises(RuntimeError, match="LLM quota exceeded"):
                _poll_until_complete.__wrapped__("http://presenton:5000", "task-1")


class TestGeneratePptx:
    def _setup_mocks(
        self,
        mock_post: MagicMock,
        mock_get: MagicMock,
        presenton_url: str = "http://presenton:5000",
    ) -> None:
        mock_post.return_value = _mock_response({"id": "task-abc"})
        completed = {
            "status": "completed",
            "data": {"path": "/app_data/exports/My Slides.pptx"},
        }
        pptx_resp = MagicMock()
        pptx_resp.raise_for_status.return_value = None
        pptx_resp.content = b"FAKE_PPTX_CONTENT"
        mock_get.side_effect = [_mock_response(completed), pptx_resp]

    @patch("app.services.presenton.settings")
    @patch("httpx.get")
    @patch("httpx.post")
    def test_happy_path_returns_pptx_bytes(
        self, mock_post: MagicMock, mock_get: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.presenton_url = "http://presenton:5000"
        self._setup_mocks(mock_post, mock_get)
        result = generate_pptx(["# Slide 1\n- point"], "My Title")
        assert result == b"FAKE_PPTX_CONTENT"

    @patch("app.services.presenton.settings")
    @patch("httpx.get")
    @patch("httpx.post")
    def test_submit_uses_correct_payload(
        self, mock_post: MagicMock, mock_get: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.presenton_url = "http://presenton:5000"
        self._setup_mocks(mock_post, mock_get)
        generate_pptx(["# Slide 1\n- point", "# Slide 2\n- other"], "Test Title")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["content"] == "Test Title"
        assert payload["slides_markdown"] == ["# Slide 1\n- point", "# Slide 2\n- other"]
        assert payload["n_slides"] == 2

    @patch("app.services.presenton.settings")
    @patch("httpx.get")
    @patch("httpx.post")
    def test_error_status_raises(
        self, mock_post: MagicMock, mock_get: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.presenton_url = "http://presenton:5000"
        mock_post.return_value = _mock_response({"id": "task-err"})
        mock_get.return_value = _mock_response({"status": "error", "error": "out of memory"})
        with pytest.raises(RuntimeError, match="out of memory"):
            generate_pptx(["# Slide\n- point"], "Title")
