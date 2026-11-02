# Readable EKG result (75-minute milestone)

Goal: the result window shows the predicted rhythm and model score first, with the raw response underneath for troubleshooting. Everything is built and tested offline with synthetic data (no API key, no credits).

## 1. Identify the two fields (10 min)
- Open your saved response in VS Code. Find the predicted class and the score **for that same class**. Don't assume the first number or first class in a list is the prediction.
- Write down exact keys and nesting. Current assumption (verify!): `predictions.labelName` and `predictions.score`.
- Make a synthetic copy with the same structure, a teaching label, and no IDs, URLs, or metadata: `synthetic_response.json`.

## 2. Formatter (20 min) — `ekg_result.py`
`format_prediction(label, score)` takes two values so display can be tested apart from the API. It assumes a 0–1 score scale. A score of 0 is valid; `True`, missing, or out-of-range scores show "unavailable" while the label stays visible. `summarize_response(payload)` extracts the two fields and returns "Prediction unavailable" if the structure is missing.

## 3. Connect to the window (20 min) — `call_api()` in `ekg_test.py`
- The JSON response is parsed once; successful (HTTP 2xx) responses get the summary above a `--- Raw response ---` divider.
- HTTP errors keep their "API error" path and never show a prediction.
- Unfamiliar shape → "Prediction unavailable", raw response still visible.
- Upload and API-key code is unchanged.

## 4. Test offline (25 min)
Run: `python -m unittest test_ekg_result -v`

| Case | Expected |
|---|---|
| Synthetic AFib, 0.9 | `Predicted rhythm: AFib` / `Model score: 90.0%` |
| Score 0 | `0.0%`, not unavailable |
| Missing score, `true`, 1.4 | Label visible; score unavailable |
| Empty label, or metadata only | `Prediction unavailable`, no traceback |
| API error | Shown as error, never as prediction |

## Done when
The window renders synthetic success and failure cases, the raw response stays available, and no test needs an API key. "Model score" is deliberately distinct from measured accuracy.

## Next step
Add an expected-rhythm field for teaching cases so you can compare the model's prediction with a known label, not just its confidence.
