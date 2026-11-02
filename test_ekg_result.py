import copy
import json
import unittest
from pathlib import Path

from ekg_result import UNAVAILABLE, format_prediction, summarize_response

BASE = json.loads(Path(__file__).with_name("synthetic_response.json").read_text())


def variant(**changes):
    payload = copy.deepcopy(BASE)
    payload["predictions"].update(changes)
    return payload


class SummarizeTests(unittest.TestCase):
    def test_normal(self):
        text = summarize_response(BASE)
        self.assertIn("Predicted rhythm: AFib\nModel score: 90.0%", text)

    def test_zero_score(self):
        self.assertIn("Model score: 0.0%", summarize_response(variant(score=0)))

    def test_bad_scores_keep_label(self):
        for bad in (None, True, 1.4, -0.1, "0.9", float("nan")):
            with self.subTest(score=bad):
                text = summarize_response(variant(score=bad))
                self.assertIn("Predicted rhythm: AFib", text)
                self.assertIn("Model score: unavailable", text)

    def test_missing_score_key(self):
        payload = copy.deepcopy(BASE)
        del payload["predictions"]["score"]
        self.assertIn("Model score: unavailable", summarize_response(payload))

    def test_empty_or_bad_label(self):
        for bad in ("", "   ", None, 5):
            with self.subTest(label=bad):
                self.assertEqual(summarize_response(variant(labelName=bad)), UNAVAILABLE)

    def test_unfamiliar_shapes(self):
        for payload in ({"type": "x", "latency": 1}, {}, [], None, "text",
                        {"predictions": []}, {"predictions": None}):
            with self.subTest(payload=payload):
                self.assertEqual(summarize_response(payload), UNAVAILABLE)

    def test_label_whitespace_stripped(self):
        self.assertIn("Predicted rhythm: AFib\n", format_prediction("  AFib ", 0.5))


if __name__ == "__main__":
    unittest.main()
