"""
Same explainable scoring formula as fastapi-service/app/routers/security_score.py.

Duplicated on purpose, not by accident: this service needs the number to
put in a PDF, that service needs it for an API response, and neither
should have a runtime dependency on the other just to compute one integer.
If the formula ever changes, both copies need the same edit - acceptable
for a formula this small (see fastapi-service's password-strength.py for
the same tradeoff, made explicit there too).
"""


def compute_security_score(status_counts: dict[str, int]) -> tuple[int, str]:
    total = sum(status_counts.values())
    malicious = status_counts.get("MALICIOUS", 0)
    suspicious = status_counts.get("SUSPICIOUS", 0)
    clean = status_counts.get("CLEAN", 0)

    if total == 0:
        return 100, "No scans yet - starting score is neutral until there's activity to base it on."

    penalty = (malicious * 20) + (suspicious * 5)
    score = max(0, 100 - penalty)
    explanation = (
        f"{total} scan(s): {clean} clean, {suspicious} suspicious, {malicious} malicious. "
        f"Each malicious result costs 20 points, each suspicious costs 5, floor of 0."
    )
    return score, explanation
