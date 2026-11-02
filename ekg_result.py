UNAVAILABLE = "Prediction unavailable"


def format_prediction(label, score):
    if not isinstance(label, str) or not label.strip():
        return UNAVAILABLE

    # Unlike a simple truthiness check, this accepts a genuine score of 0.
    valid_score = type(score) in (int, float) and 0 <= score <= 1
    score_text = f"{score:.1%}" if valid_score else "unavailable"
    return (
        f"Predicted rhythm: {label.strip()}\n"
        f"Model score: {score_text}\n"
        "Experimental teaching output — not a clinical diagnosis."
    )


def summarize_response(payload):
    # Verified path: payload["predictions"]["labelName"] and ["score"].
    # Update these keys if your saved response differs.
    predictions = payload.get("predictions") if isinstance(payload, dict) else None
    if not isinstance(predictions, dict):
        return UNAVAILABLE
    return format_prediction(predictions.get("labelName"), predictions.get("score"))
