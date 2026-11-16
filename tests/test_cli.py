from __future__ import annotations

import unittest

from src.cli import configure_utf8


class ReconfigurableStream:
    def __init__(self) -> None:
        self.encoding = None
        self.errors = None

    def reconfigure(self, *, encoding, errors):
        self.encoding = encoding
        self.errors = errors


class CliEncodingTests(unittest.TestCase):
    def test_standard_stream_is_reconfigured_to_utf8(self) -> None:
        stream = ReconfigurableStream()
        configure_utf8(stream)
        self.assertEqual(stream.encoding, "utf-8")
        self.assertEqual(stream.errors, "strict")


if __name__ == "__main__":
    unittest.main()
