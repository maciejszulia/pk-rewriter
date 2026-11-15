import unittest
from unittest import mock

from fastapi.testclient import TestClient

from pk_rewriter import api, rewrite as rw

CLEAN = {"message": {"content": "Zamknij okno O1."}, "prompt_eval_count": 1, "eval_count": 1, "eval_duration": 1}


class Api(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        patcher = mock.patch.object(api, "MODELS", ["qwen3.5:4b", "qwen3.5:0.8b"])
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, **body):
        with mock.patch.object(rw, "chat", return_value=CLEAN):
            return self.client.post("/rewrite", json=body)

    def test_rewrite_ok(self):
        r = self.post(text="Zamknij okno.", model="qwen3.5:0.8b", rounds=1)
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.json()["text"], r.json()["ok"], r.json()["rounds"]), ("Zamknij okno O1.", True, 1))

    def test_text_length_from_1_to_2000(self):
        self.assertEqual(self.post(text="x" * 2000).status_code, 200)
        self.assertEqual(self.post(text="x" * 2001).status_code, 422)
        self.assertEqual(self.post(text="").status_code, 422)
        self.assertEqual(self.post(text="   ").status_code, 422)

    def test_model_from_list(self):
        self.assertEqual(self.post(text="Zamknij okno.", model="llama3").status_code, 422)

    def test_rounds_from_1_to_3(self):
        for n, code in ((0, 422), (1, 200), (3, 200), (4, 422)):
            self.assertEqual(self.post(text="Zamknij okno.", rounds=n).status_code, code, n)

    def test_ollama_down_gives_502(self):
        with mock.patch.object(rw, "chat", side_effect=ConnectionRefusedError("refused")):
            r = self.client.post("/rewrite", json={"text": "Zamknij okno."})
        self.assertEqual(r.status_code, 502)

    def test_lint(self):
        r = self.client.post("/lint", json={"text": "Kopie bazy należy usuwać regularnie."})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sorted(v["code"] for v in r.json()["violations"]), ["A5", "B1"])
        self.assertEqual(self.client.post("/lint", json={"text": ""}).status_code, 422)

    def test_health_and_page(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError):
            r = self.client.get("/health")
        self.assertEqual(r.json(), {"status": "ok", "ollama": False, "models": ["qwen3.5:4b", "qwen3.5:0.8b"]})
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("aria-live", page.text)


if __name__ == "__main__":
    unittest.main()
