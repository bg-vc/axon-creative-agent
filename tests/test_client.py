import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from axon_creative.client import ComfyUIClient
from axon_creative.errors import ComfyUIError


def response(payload: bytes):
    context = Mock()
    context.read.return_value = payload
    manager = Mock()
    manager.__enter__ = Mock(return_value=context)
    manager.__exit__ = Mock(return_value=False)
    return manager


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = ComfyUIClient("http://127.0.0.1:8188")

    @patch("axon_creative.client.request.urlopen")
    def test_get_and_submit(self, urlopen):
        urlopen.side_effect = [
            response(json.dumps({"ok": True}).encode()),
            response(json.dumps({"prompt_id": "prompt-1", "number": 1}).encode()),
        ]
        self.assertEqual(self.client.get("/stats"), {"ok": True})
        prompt_id = self.client.submit(
            {"1": {"class_type": "Test", "inputs": {}}}, "client"
        )
        self.assertEqual(prompt_id, "prompt-1")
        submitted = json.loads(urlopen.call_args_list[1].args[0].data)
        self.assertEqual(submitted["client_id"], "client")

    @patch("axon_creative.client.request.urlopen")
    def test_invalid_json_is_reported(self, urlopen):
        urlopen.return_value = response(b"not json")
        with self.assertRaises(ComfyUIError):
            self.client.get("/bad-json")

    def test_unsafe_upload_filename_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad"name.png'
            with self.assertRaises(ComfyUIError):
                self.client.upload_image(path, "inputs")


if __name__ == "__main__":
    unittest.main()
