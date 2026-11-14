"""Recette navigateur du formulaire hybride (Firefox headless via WebDriver).

Active uniquement avec FORGE_E2E=1 et geckodriver + firefox disponibles :
    FORGE_E2E=1 python3 -m unittest tests.test_e2e_firefox -v
Protocole WebDriver W3C pilote avec urllib : aucune dependance tierce.
"""
import base64
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
import urllib.request

from server import Handler, ThreadingHTTPServer

ELEMENT = "element-6066-11e4-a52e-4f735466cecf"
ENABLED = os.environ.get("FORGE_E2E") == "1" and shutil.which("geckodriver") and shutil.which("firefox")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@unittest.skipUnless(ENABLED, "FORGE_E2E=1, geckodriver et firefox requis")
class FirefoxFormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = "http://127.0.0.1:%d" % cls.server.server_address[1]
        # Firefox snap n'accede pas au /tmp prive : profil dans un dossier ignore du depot.
        root = os.environ.get("FORGE_E2E_TMP") or os.path.join(os.getcwd(), ".tmp-e2e")
        os.makedirs(root, exist_ok=True)
        cls.tmp = tempfile.mkdtemp(prefix="forge-e2e-", dir=root)
        port = free_port()
        cls.driver_url = "http://127.0.0.1:%d" % port
        cls.driver = subprocess.Popen(["geckodriver", "--port", str(port), "--profile-root", cls.tmp], stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, env=dict(os.environ, TMPDIR=cls.tmp))
        for _ in range(100):
            try:
                cls.call("GET", "/status")
                break
            except OSError:
                time.sleep(0.1)
        caps = {"capabilities": {"alwaysMatch": {"browserName": "firefox",
                                                 "moz:firefoxOptions": {"args": ["-headless"]}}}}
        cls.session = cls.call("POST", "/session", caps)["sessionId"]

    @classmethod
    def tearDownClass(cls):
        try:
            cls.call("DELETE", "/session/" + cls.session)
        finally:
            cls.driver.terminate()
            cls.driver.wait(10)
            cls.server.shutdown()
            cls.server.server_close()
            shutil.rmtree(cls.tmp, ignore_errors=True)

    @classmethod
    def call(cls, method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(cls.driver_url + path, data=data, method=method,
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read())["value"]

    def cmd(self, method, path, payload=None):
        return self.call(method, "/session/%s%s" % (self.session, path), payload)

    def find(self, css):
        return self.cmd("POST", "/element", {"using": "css selector", "value": css})[ELEMENT]

    def js(self, script, *args):
        return self.cmd("POST", "/execute/sync", {"script": script, "args": list(args)})

    def click(self, css):
        self.cmd("POST", "/element/%s/click" % self.find(css), {})

    def wait(self, script, timeout=15):
        end = time.time() + timeout
        while time.time() < end:
            if self.js(script):
                return
            time.sleep(0.1)
        self.fail("Condition non atteinte : " + script)

    def visible(self, css):
        return self.cmd("GET", "/element/%s/displayed" % self.find(css))

    def screenshot(self, name):
        """Capture optionnelle (FORGE_E2E_SCREENSHOTS=dossier) pour controle visuel."""
        target = os.environ.get("FORGE_E2E_SCREENSHOTS")
        if target:
            with open(os.path.join(target, name + ".png"), "wb") as handle:
                handle.write(base64.b64decode(self.cmd("GET", "/screenshot")))

    def test_full_journey(self):
        self.cmd("POST", "/url", {"url": self.base + "/"})
        self.wait("return document.querySelectorAll('#project_type option').length > 0")
        # Section 1 : badge d'erreur tant que le nom est invalide.
        self.assertFalse(self.js("return document.querySelector('[data-goto=\"0\"] .badge').hidden"))
        self.cmd("POST", "/element/%s/value" % self.find("#name"), {"text": "e2e-demo"})
        self.js("const s=document.querySelector('#project_type'); s.value='api'; s.dispatchEvent(new Event('change',{bubbles:true}))")
        self.wait("return document.querySelector('[data-goto=\"0\"] .badge').hidden")
        self.click("#next")
        # Section 2 : questions conditionnelles.
        self.assertFalse(self.visible('[data-tech="pytest"]'))
        self.click("#tech-python")
        self.wait("return !document.querySelector('[data-tech=\"pytest\"]').hidden")
        self.assertTrue(self.visible('[data-tech="python"] .version'))
        self.click("#tech-fastapi")
        self.click("#tech-pytest")
        self.screenshot("technologies")
        self.assertTrue(self.js("return document.querySelector('#tech-flask').disabled"))
        # Retrait en cascade puis reselection.
        self.click("#tech-python")
        self.wait("return !document.querySelector('#tech-fastapi').checked && !document.querySelector('#tech-pytest').checked")
        for css in ("#tech-python", "#tech-fastapi", "#tech-pytest"):
            self.click(css)
        # Section 3 : agents, puis verification.
        self.click('[data-goto="2"]')
        self.click('input[name="agent"][value="claude"]')
        self.click('[data-goto="4"]')
        self.click("#check")
        self.wait("return !document.querySelector('#download').disabled")
        files = self.js("return [...document.querySelectorAll('#files button')].map(b => b.textContent)")
        self.assertIn("AGENTS.md", files)
        self.assertIn("CLAUDE.md", files)
        self.assertIn("e2e-demo", self.js("return document.querySelector('#content').textContent"))
        self.screenshot("verification")
        # Une modification invalide l'apercu valide.
        self.click('[data-goto="0"]')
        self.cmd("POST", "/element/%s/value" % self.find("#description"), {"text": "x"})
        self.assertTrue(self.js("return document.querySelector('#download').disabled"))


if __name__ == "__main__":
    unittest.main()
