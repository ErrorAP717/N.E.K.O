"""ComputerUse prefers the renderer frame and falls back to native capture."""

from __future__ import annotations

import base64
from io import BytesIO

import pytest
from PIL import Image

from brain import computer_use


class _Response:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _Client:
    def __init__(self, response: _Response):
        self.response = response

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def post(self, url):
        assert url.endswith("/api/capture/computer-use")
        return self.response


@pytest.mark.unit
def test_computer_use_decodes_renderer_frame_before_native_capture(monkeypatch):
    buffer = BytesIO()
    Image.new("RGB", (32, 24), "red").save(buffer, format="PNG")
    data_url = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
    monkeypatch.setattr(computer_use.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        computer_use.httpx, "Client", lambda **_kwargs: _Client(_Response(200, {"image": data_url}))
    )
    monkeypatch.setattr(
        computer_use, "capture_desktop_screenshot",
        lambda: pytest.fail("native screenshot should not run after renderer success"),
    )
    image = computer_use._capture_computer_use_frame()
    assert image.size == (32, 24)
    assert image.getpixel((0, 0)) == (255, 0, 0)


@pytest.mark.unit
def test_computer_use_falls_back_when_renderer_is_unavailable(monkeypatch):
    native = Image.new("RGB", (16, 12), "blue")
    monkeypatch.setattr(computer_use.platform, "system", lambda: "Linux")
    monkeypatch.setattr(
        computer_use.httpx, "Client", lambda **_kwargs: _Client(_Response(503, {"error": "no_renderer"}))
    )
    monkeypatch.setattr(computer_use, "capture_desktop_screenshot", lambda: native)
    assert computer_use._capture_computer_use_frame() is native
