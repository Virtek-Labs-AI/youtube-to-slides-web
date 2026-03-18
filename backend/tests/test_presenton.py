from unittest.mock import MagicMock, patch

import pytest

from app.services.presenton import generate_pptx


def _mock_response(json_data: object, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    resp.is_error = status_code >= 400
    resp.content = b"PPTX_BYTES"
    return resp


class TestGeneratePptx:
    def _setup_mocks(
        self,
        mock_post: MagicMock,
        mock_get: MagicMock,
    ) -> None:
        mock_post.return_value = _mock_response({"presentation_id": "abc-123"})
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
        assert "export_as" not in payload
        assert payload["n_slides"] == 2

    @patch("app.services.presenton.settings")
    @patch("httpx.get")
    @patch("httpx.post")
    def test_uses_sync_generate_endpoint(
        self, mock_post: MagicMock, mock_get: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.presenton_url = "http://presenton:5000"
        mock_settings.presenton_template = "modern"
        self._setup_mocks(mock_post, mock_get)
        generate_pptx(["# Slide 1\n- point"], "Title")
        called_url = mock_post.call_args[0][0]
        assert called_url.endswith("/api/v1/ppt/presentation/generate")

    @patch("app.services.presenton.settings")
    @patch("httpx.get")
    @patch("httpx.post")
    def test_export_uses_shapes_endpoint(
        self, mock_post: MagicMock, mock_get: MagicMock, mock_settings: MagicMock
    ) -> None:
        mock_settings.presenton_url = "http://presenton:5000"
        mock_settings.presenton_template = "modern"
        self._setup_mocks(mock_post, mock_get)
        generate_pptx(["# Slide 1\n- point"], "Title")
        called_url = mock_get.call_args[0][0]
        assert called_url.endswith("/api/v1/ppt/presentation/export/pptx")
        called_params = mock_get.call_args.kwargs["params"]
        assert called_params["presentationId"] == "abc-123"

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
