#  Copyright (c) 2026. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import importlib
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

ros2_docs = None
IMPORT_OK = False
IMPORT_ERROR = ""

# Ensure local src/ is importable when running tests without package install.
REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

for module_path in ("src.rosa.tools.ros2_docs", "rosa.tools.ros2_docs"):
    try:
        ros2_docs = importlib.import_module(module_path)
        IMPORT_OK = True
        break
    except ModuleNotFoundError as exc:
        IMPORT_ERROR = str(exc)


@unittest.skipUnless(
    IMPORT_OK, f"ros2_docs module not available in this environment: {IMPORT_ERROR}"
)
class TestROS2DocsTools(unittest.TestCase):
    def test_is_allowed_url_accepts_official_domains(self):
        ok_root, _ = ros2_docs._is_allowed_url("https://docs.ros.org/en/humble/")
        ok_sub, _ = ros2_docs._is_allowed_url(
            "https://foo.design.ros2.org/some/page.html"
        )
        self.assertTrue(ok_root)
        self.assertTrue(ok_sub)

    def test_is_allowed_url_rejects_non_whitelist(self):
        ok, reason = ros2_docs._is_allowed_url("https://example.com/ros2")
        self.assertFalse(ok)
        self.assertIn("not in the allowed ROS docs whitelist", reason)

    def test_is_allowed_url_rejects_non_http_scheme(self):
        ok, reason = ros2_docs._is_allowed_url("file:///tmp/doc.html")
        self.assertFalse(ok)
        self.assertIn("Only http/https URLs are allowed", reason)

    @patch("src.rosa.tools.ros2_docs._http_get")
    def test_ros2_docs_search_filters_to_whitelist(self, mock_http_get):
        mock_http_get.return_value = """
        <a class="result__a" href="https://docs.ros.org/en/humble/p/ros2cli/">ROS2 CLI</a>
        <div class="result__snippet">official docs snippet</div>
        <a class="result__a" href="https://evil.example.org/ros2/cli">Bad Source</a>
        <div class="result__snippet">bad snippet</div>
        """

        result = ros2_docs.ros2_docs_search.invoke({"query": "ros2 cli"})

        self.assertIn("results", result)
        self.assertEqual(result["results_count"], 1)
        self.assertEqual(result["results"][0]["url"], "https://docs.ros.org/en/humble/p/ros2cli/")

    @patch("src.rosa.tools.ros2_docs._http_get")
    def test_ros2_docs_search_http_failure_returns_error(self, mock_http_get):
        mock_http_get.side_effect = RuntimeError("network timeout")
        result = ros2_docs.ros2_docs_search.invoke({"query": "ros2 topic echo"})
        self.assertIn("error", result)
        self.assertIn("Failed to search ROS2 docs", result["error"])

    @patch("src.rosa.tools.ros2_docs._http_get")
    def test_ros2_docs_fetch_rejects_non_whitelist_url(self, mock_http_get):
        result = ros2_docs.ros2_docs_fetch.invoke({"url": "https://example.com"})
        self.assertIn("error", result)
        mock_http_get.assert_not_called()

    @patch("src.rosa.tools.ros2_docs._http_get")
    def test_ros2_docs_fetch_truncates_and_strips_html(self, mock_http_get):
        mock_http_get.return_value = "<html><body>" + ("a" * 2005) + "</body></html>"
        result = ros2_docs.ros2_docs_fetch.invoke(
            {"url": "https://docs.ros.org/en/humble/", "max_chars": 1000}
        )

        self.assertEqual(result["max_chars"], 1000)
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["content"]), 1000)

    @patch("src.rosa.tools.ros2_docs._http_get")
    def test_ros2_docs_fetch_failure_returns_error(self, mock_http_get):
        mock_http_get.side_effect = Exception("cannot fetch")
        result = ros2_docs.ros2_docs_fetch.invoke(
            {"url": "https://docs.ros.org/en/humble/"}
        )
        self.assertIn("error", result)
        self.assertIn("Failed to fetch ROS2 docs page", result["error"])

    def test_ros2_docs_extract_cli_returns_structured_fields(self):
        page_text = (
            "Usage: ros2 topic echo /chatter --once\n"
            "--once  Echo one message and exit\n"
            "--spin-time  Wait for this many seconds\n"
            "ros2 topic echo /chatter --once\n"
        )
        result = ros2_docs.ros2_docs_extract_cli.invoke(
            {"command": "ros2 topic echo", "page_text": page_text}
        )

        self.assertEqual(result["command"], "ros2 topic echo")
        self.assertIn("usage", result)
        self.assertIn("key_args", result)
        self.assertIn("examples", result)
        self.assertEqual(result["confidence"], "high")
        self.assertTrue(any("--once" in arg for arg in result["key_args"]))

    def test_ros2_docs_extract_cli_accepts_json_page_text(self):
        as_json = json.dumps(
            {
                "content": "Usage: ros2 service call /foo\n--help Show help\nros2 service call /foo std_srvs/srv/Empty {}"
            }
        )
        result = ros2_docs.ros2_docs_extract_cli.invoke(
            {"command": "ros2 service call", "page_text": as_json}
        )
        self.assertIn("usage", result)
        self.assertIn("examples", result)
        self.assertNotIn("error", result)


if __name__ == "__main__":
    unittest.main()
