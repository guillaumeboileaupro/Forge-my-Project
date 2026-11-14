import http.client
import io
import json
import threading
import unittest
import zipfile

from server import Handler, ThreadingHTTPServer


CONFIG = {
    "name": "server-test",
    "description": "Server integration test",
    "language": "python",
    "agent": "codex",
    "deployment": "none",
    "security": "strict",
}


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=2)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_index_and_security_headers(self):
        status, headers, body = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"Forge-my-Project", body)
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")

    def test_static_assets_are_served_with_strict_csp(self):
        for path, media in (("/css/app.css", "text/css"), ("/js/app.js", "text/javascript")):
            with self.subTest(path=path):
                status, headers, body = self.request("GET", path)
                self.assertEqual(status, 200)
                self.assertTrue(headers["Content-Type"].startswith(media))
                self.assertTrue(body)
                self.assertNotIn("'unsafe-inline'", headers["Content-Security-Policy"])

    def test_unknown_route_returns_not_found(self):
        status, _, _ = self.request("GET", "/missing")
        self.assertEqual(status, 404)

    def test_generate_returns_safe_zip(self):
        body = json.dumps(CONFIG)
        status, headers, content = self.request(
            "POST",
            "/generate",
            body,
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "application/zip")
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="server-test.zip"')
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            self.assertIn("server-test/AGENTS.md", archive.namelist())

    def test_rejects_non_json_content_type(self):
        status, _, _ = self.request("POST", "/generate", json.dumps(CONFIG))
        self.assertEqual(status, 415)

    def test_rejects_foreign_host(self):
        status, _, _ = self.request(
            "POST",
            "/generate",
            json.dumps(CONFIG),
            {"Content-Type": "application/json", "Host": "attacker.example"},
        )
        self.assertEqual(status, 403)

    def test_rejects_invalid_and_oversized_bodies(self):
        status, _, _ = self.request(
            "POST", "/generate", "{", {"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)
        status, _, _ = self.request(
            "POST", "/generate", b"x" * 16385, {"Content-Type": "application/json"}
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
