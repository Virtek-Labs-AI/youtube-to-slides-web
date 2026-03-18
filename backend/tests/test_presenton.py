from unittest.mock import MagicMock, patch

import pytest

from app.services.presenton import _build_download_url, generate_pptx


def _mock_response(json_data: object, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    resp.is_error = status_code >= 400
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


class TestGeneratePptx:
    def _setup_mocks(
        self,
        mock_post: MagicMock,
        mock_get: MagicMock,
        presenton_url: str = "http://presenton:5000",
    ) -> None:
        mock_post.return_value = _mock_response({"path": "/app_data/exports/My Slides.pptx"})
        pptx_resp = MagicMock()
        pptx_resp.raise_for_status.return_value = None
        pptx_resp.content = b"FAKE_PPTX_CONTENT"
        mock_get.return_value = pptx_resp

    @patch("app.services.presenton.settings")
    @patch("httpx.get")
    @patch("httpx.post")
    def test_happy_path_returns_pptx_bytes(
        self, mock_post: MagicMock, mock_get: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.presenton_url = "http://presenton:5000"
        mock_settings.presenton_template = "modern"
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
        mock_settings.presenton_template = "modern"
        self._setup_mocks(mock_post, mock_get)
        generate_pptx(["# Slide 1\n- point", "# Slide 2\n- other"], "Test Title")
        payload = mock_post.call_args.kwargs["json"]
        assert payload["content"] == "# Slide 1\n- point\n\n# Slide 2\n- other"
        assert "slides_markdown" not in payload
        assert payload["n_slides"] == 2

    @patch("app.services.presenton.settings")
    @patch("httpx.get")
    @patch("httpx.post")
    def test_uses_sync_endpoint(
        self, mock_post: MagicMock, mock_get: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.presenton_url = "http://presenton:5000"
        mock_settings.presenton_template = "modern"
        self._setup_mocks(mock_post, mock_get)
        generate_pptx(["# Slide 1\n- point"], "Title")
        called_url = mock_post.call_args[0][0]
        assert "/generate/async" not in called_url
        assert called_url.endswith("/api/v1/ppt/presentation/generate")

    @patch("app.services.presenton.settings")
    @patch("httpx.get")
    @patch("httpx.post")
    def test_api_error_raises(
        self, mock_post: MagicMock, mock_get: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.presenton_url = "http://presenton:5000"
        mock_settings.presenton_template = "modern"
        mock_post.return_value = _mock_response({"detail": "Internal error"}, status_code=500)
        mock_post.return_value.raise_for_status.side_effect = Exception("500 error")
        with pytest.raises(Exception, match="500 error"):
            generate_pptx(["# Slide\n- point"], "Title")
