"""Tests for presentation_tasks retry/fallback logic.

Covers:
- _generate_with_presenton retries on each transient error type
- Fallback to render_pptx after retries are exhausted
- Warning log with metric field emitted on fallback
- RuntimeError from Presenton triggers fallback (not hard failure)
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.tasks.presentation_tasks import _PRESENTON_TRANSIENT_ERRORS, _generate_with_presenton


# ---------------------------------------------------------------------------
# _generate_with_presenton — retry behaviour
# ---------------------------------------------------------------------------

def _make_transient_exc(exc_class: type) -> Exception:
    """Construct a transient exception instance; HTTPStatusError requires extra kwargs."""
    if exc_class is httpx.HTTPStatusError:
        return exc_class("boom", request=MagicMock(), response=MagicMock())
    return exc_class("boom")


class TestGenerateWithPresenton:
    """_generate_with_presenton retries on every type in _PRESENTON_TRANSIENT_ERRORS."""

    @pytest.mark.parametrize("exc_class", _PRESENTON_TRANSIENT_ERRORS)
    def test_raises_on_single_call(self, exc_class: type) -> None:
        """The unwrapped function propagates each transient error on a single call."""
        exc = _make_transient_exc(exc_class)
        mock_generate = MagicMock(side_effect=exc)
        with patch("app.tasks.presentation_tasks.presenton_service.generate_pptx", mock_generate):
            with pytest.raises(type(exc)):
                _generate_with_presenton.__wrapped__(["slide"], "title")

    def test_returns_bytes_on_success(self) -> None:
        """Returns bytes from presenton_service.generate_pptx on success."""
        expected = b"pptx-bytes"
        with patch("app.tasks.presentation_tasks.presenton_service.generate_pptx", return_value=expected):
            result = _generate_with_presenton.__wrapped__(["# Slide 1"], "My Title")
        assert result == expected

    def test_retries_connect_error_three_times(self) -> None:
        """Retries exactly 3 times (stop_after_attempt=3) on ConnectError before re-raising."""
        call_count = 0

        def flaky(*_args, **_kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("refused")
            return b"success"

        with patch("app.tasks.presentation_tasks.presenton_service.generate_pptx", side_effect=flaky):
            result = _generate_with_presenton(["# Slide"], "Title")

        assert result == b"success"
        assert call_count == 3

    def test_reraises_after_all_attempts_exhausted(self) -> None:
        """Re-raises ConnectError after all 3 attempts fail (reraise=True)."""
        with patch(
            "app.tasks.presentation_tasks.presenton_service.generate_pptx",
            side_effect=httpx.ConnectError("refused"),
        ):
            with pytest.raises(httpx.ConnectError):
                _generate_with_presenton(["# Slide"], "Title")


# ---------------------------------------------------------------------------
# Fallback path in generate_presentation
# ---------------------------------------------------------------------------

class TestGeneratePresentationFallback:
    """generate_presentation falls back to render_pptx when Presenton fails."""

    def _make_presentation(self, video_id: str = "abc123") -> MagicMock:
        p = MagicMock()
        p.video_id = video_id
        p.title = None
        p.pptx_path = None
        return p

    @pytest.fixture()
    def _common_patches(self):
        """Patches common to all fallback tests."""
        slides_data = {"slides": [{"title": "T", "bullets": [], "refs": []}]}
        with (
            patch("app.tasks.presentation_tasks.Session") as mock_session_cls,
            patch("app.tasks.presentation_tasks.get_transcript", return_value="transcript"),
            patch("app.tasks.presentation_tasks.generate_slides_from_transcript", return_value=slides_data),
            patch("app.tasks.presentation_tasks.format_slides_as_markdown", return_value=["# T"]),
            patch("app.tasks.presentation_tasks.inject_references", return_value=b"injected"),
            patch("app.tasks.presentation_tasks._save_pptx_bytes", return_value="/tmp/out.pptx"),
            patch("app.tasks.presentation_tasks.render_pptx", return_value="/tmp/fallback.pptx") as mock_render,
            patch("app.tasks.presentation_tasks.storage.is_s3_enabled", return_value=False),
            patch("app.tasks.presentation_tasks.settings") as mock_settings,
        ):
            mock_settings.presenton_url = "http://presenton:5000"
            mock_settings.redis_url = "redis://localhost:6379/0"
            mock_settings.database_url = "postgresql://localhost/test"
            mock_settings.storage_path = "/tmp/slides"

            presentation = self._make_presentation()
            mock_db = MagicMock()
            mock_db.get.return_value = presentation
            mock_session_cls.return_value.__enter__.return_value = mock_db

            yield {
                "mock_render": mock_render,
                "presentation": presentation,
                "mock_db": mock_db,
            }

    @pytest.mark.parametrize(
        "exc",
        [
            httpx.ConnectError("refused"),
            httpx.TimeoutException("timeout"),
            httpx.HTTPStatusError("502", request=MagicMock(), response=MagicMock()),
            TimeoutError("presenton timed out"),
            RuntimeError("Presenton generation failed: quota exceeded"),
        ],
    )
    def test_falls_back_to_render_pptx_on_presenton_failure(self, _common_patches, exc: Exception) -> None:
        """Falls back to render_pptx for every error type that Presenton can raise."""
        from app.tasks.presentation_tasks import generate_presentation

        with patch(
            "app.tasks.presentation_tasks._generate_with_presenton",
            side_effect=exc,
        ):
            generate_presentation(1)

        _common_patches["mock_render"].assert_called_once()

    def test_warning_log_emitted_with_metric_field(self, _common_patches, caplog) -> None:
        """Warning log includes metric='presenton_fallback_total' on fallback."""
        from app.tasks.presentation_tasks import generate_presentation

        with (
            patch(
                "app.tasks.presentation_tasks._generate_with_presenton",
                side_effect=httpx.ConnectError("refused"),
            ),
            patch("app.tasks.presentation_tasks.logger") as mock_logger,
        ):
            generate_presentation(1)

        mock_logger.warning.assert_called_once()
        _, kwargs = mock_logger.warning.call_args
        assert kwargs.get("metric") == "presenton_fallback_total"

    def test_presentation_status_done_after_fallback(self, _common_patches) -> None:
        """Presentation status is set to done even when Presenton fallback is used."""
        from app.db.models import PresentationStatus
        from app.tasks.presentation_tasks import generate_presentation

        with patch(
            "app.tasks.presentation_tasks._generate_with_presenton",
            side_effect=httpx.ConnectError("refused"),
        ):
            generate_presentation(1)

        presentation = _common_patches["presentation"]
        assert presentation.status == PresentationStatus.done
