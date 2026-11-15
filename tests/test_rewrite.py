import csv
import io
import json
import unittest
from pathlib import Path
from unittest import mock

from pk_rewriter import pklint, rewrite as rw

ROOT = Path(__file__).resolve().parent.parent
CLEAN = "Administrator usuwa kopię bazy B1, która ma więcej niż 30 dni."
DIRTY = "Kopie bazy należy usuwać po 30 dniach."


def reply(text):
    return {"message": {"role": "assistant", "content": text}, "prompt_eval_count": 600, "eval_count": 20,
            "eval_duration": 2_000_000_000}


def fake_chat(*texts):
    """Model stand-in: returns the given texts in order and records every call."""
    calls = []

    def chat(model, messages):
        calls.append(messages)
        return reply(texts[len(calls) - 1])
    return chat, calls


class Loop(unittest.TestCase):
    def test_selfcheck(self):
        self.assertEqual(pklint.selfcheck(), "ok")

    def test_clean_first_answer_stops_after_1_call(self):
        chat, calls = fake_chat(CLEAN)
        with mock.patch.object(rw, "chat", chat):
            res = rw.rewrite("Admin kasuje kopie bazy po 30 dniach.", "m")
        self.assertEqual((res["ok"], res["rounds"], len(calls)), (True, 1, 1))
        rnd = res["history"][0]
        self.assertEqual((rnd["prompt_eval_count"], rnd["eval_count"], rnd["eval_seconds"]), (600, 20, 2.0))

    def test_repair_prompt_names_code_description_sentence_and_rule(self):
        chat, calls = fake_chat(DIRTY, CLEAN)
        with mock.patch.object(rw, "chat", chat):
            res = rw.rewrite("Kopie bazy kasujemy po 30 dniach.", "m")
        self.assertEqual((res["ok"], res["rounds"], res["text"]), (True, 2, CLEAN))
        repair = calls[1][-1]["content"]
        for part in ("B1", rw.WHAT["B1"], DIRTY, rw.RULES["B1"]):
            self.assertIn(part, repair)
        self.assertEqual([m["role"] for m in calls[1]], ["system", "user", "assistant", "user"])

    def test_at_most_3_calls(self):
        chat, calls = fake_chat(DIRTY, DIRTY, DIRTY, CLEAN)
        with mock.patch.object(rw, "chat", chat):
            res = rw.rewrite("Kopie bazy kasujemy po 30 dniach.", "m", rounds=5)
        self.assertEqual((res["ok"], res["rounds"], len(calls)), (False, 3, 3))

    def test_empty_answer_is_an_error(self):
        chat, calls = fake_chat("", "  ", "")
        with mock.patch.object(rw, "chat", chat):
            res = rw.rewrite("Zamknij okno.", "m")
        self.assertFalse(res["ok"])
        self.assertIn("pusta", calls[1][-1]["content"])

    def test_fewest_problems_wins(self):
        two = "Kopie bazy należy usuwać regularnie po 30 dniach."
        chat, _ = fake_chat(DIRTY, two, two)
        with mock.patch.object(rw, "chat", chat):
            res = rw.rewrite("Kopie bazy kasujemy po 30 dniach.", "m")
        self.assertEqual(res["text"], DIRTY)


class Numbers(unittest.TestCase):
    def test_extraction(self):
        self.assertEqual(rw.numbers("2.5 bar, 2,5 bar, godz. 02:00"), {"2,5", "2", "0"})

    def test_missing_number_fails_the_round(self):
        chat, calls = fake_chat("Sprawdź każdą pompę.", "Sprawdź każdą pompę.", "Sprawdź 3 pompy.")
        with mock.patch.object(rw, "chat", chat):
            res = rw.rewrite("Sprawdź 3 pompy.", "m")
        self.assertEqual(res["history"][0]["missing_numbers"], ["3"])
        self.assertIn("Brakuje liczb z tekstu źródłowego: 3", calls[1][-1]["content"])
        self.assertEqual((res["ok"], res["rounds"]), (True, 3))

    def test_marker_excuses_missing_numbers(self):
        self.assertEqual(rw.check("Czekaj 5 min.", "Czekaj [DO USTALENIA: czas].")[1], [])


class Client(unittest.TestCase):
    def test_payload(self):
        sent = {}

        def urlopen(req, timeout):
            sent.update(url=req.full_url, method=req.get_method(), body=json.loads(req.data))
            return io.BytesIO(json.dumps(reply(CLEAN)).encode())
        with mock.patch("urllib.request.urlopen", urlopen):
            rw.chat("qwen3.5:4b", [{"role": "user", "content": "x"}])
        self.assertTrue(sent["url"].endswith("/api/chat"))
        self.assertEqual(sent["method"], "POST")
        body = sent["body"]
        self.assertEqual((body["stream"], body["think"]), (False, False))
        self.assertEqual(body["options"], {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "seed": 42,
                                           "num_ctx": 4096, "num_predict": 1024})


class Prompt(unittest.TestCase):
    def test_rule_sentence_for_every_pklint_code(self):
        self.assertEqual(set(rw.RULES), set(pklint.CODES))

    def test_system_prompt_stays_small(self):
        # 586 tokens measured with the qwen3.5 tokenizer; 250 words keeps it under 600 tokens.
        self.assertLessEqual(len(rw.SYSTEM.split()), 250)

    def test_no_test_item_in_prompts(self):
        prompts = [rw.SYSTEM, *rw.RULES.values()]
        with open(ROOT / "data" / "items.csv", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                for value in row.values():
                    for s in pklint.sentences(value):
                        if len(s.split()) >= 3:
                            self.assertFalse(any(s in p for p in prompts), s)


if __name__ == "__main__":
    unittest.main()
