from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from .errors import ComfyUIError


class ComfyUIClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _json(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        body = None
        headers: dict[str, str] = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = request.Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ComfyUIError(f"ComfyUI {method} {path} returned {exc.code}: {detail}") from exc
        except (error.URLError, TimeoutError) as exc:
            raise ComfyUIError(f"Cannot reach ComfyUI at {self.base_url}: {exc}") from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ComfyUIError(f"ComfyUI returned invalid JSON for {path}") from exc

    def get(self, path: str) -> Any:
        return self._json("GET", path)

    def post(self, path: str, payload: dict[str, Any]) -> Any:
        return self._json("POST", path, payload)

    def upload_image(self, path: Path, subfolder: str) -> dict[str, Any]:
        if any(character in path.name for character in ('"', "\r", "\n")):
            raise ComfyUIError(f"Unsafe image filename: {path.name!r}")
        boundary = "----axoncreative" + uuid.uuid4().hex
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        chunks = []
        for name, value in (("subfolder", subfolder), ("type", "input"), ("overwrite", "false")):
            chunks.append(
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode()
            )
        chunks.append(
            (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; "
                f"filename=\"{path.name}\"\r\nContent-Type: {mime}\r\n\r\n"
            ).encode()
        )
        chunks.append(path.read_bytes())
        chunks.append(f"\r\n--{boundary}--\r\n".encode())
        req = request.Request(
            self.base_url + "/upload/image",
            data=b"".join(chunks),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (error.HTTPError, error.URLError, json.JSONDecodeError) as exc:
            raise ComfyUIError(f"Image upload failed for {path}: {exc}") from exc

    def submit(self, workflow: dict[str, Any], client_id: str) -> str:
        response = self.post("/prompt", {"prompt": workflow, "client_id": client_id})
        prompt_id = response.get("prompt_id") if isinstance(response, dict) else None
        if not prompt_id:
            raise ComfyUIError(f"ComfyUI rejected the workflow: {response}")
        return str(prompt_id)

    def download_view(self, item: dict[str, Any], destination: Path) -> Path:
        query = parse.urlencode(
            {
                "filename": item["filename"],
                "subfolder": item.get("subfolder", ""),
                "type": item.get("type", "output"),
            }
        )
        req = request.Request(self.base_url + "/view?" + query)
        try:
            with request.urlopen(req, timeout=max(self.timeout, 120.0)) as response:
                destination.write_bytes(response.read())
        except (error.HTTPError, error.URLError, OSError) as exc:
            raise ComfyUIError(f"Cannot download {item.get('filename')}: {exc}") from exc
        return destination
