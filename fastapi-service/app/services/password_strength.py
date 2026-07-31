import re

# Intentionally mirrors static/js/password-strength.js in django-service
# rule-for-rule. They can't literally share code (one runs in the
# browser, one runs here), so this is documented, deliberate duplication
# rather than an oversight - if the rules ever need to change, both files
# need the same edit. A future refactor could generate both from a single
# JSON ruleset if drift becomes a real problem; not worth the complexity
# for eight rules.
COMMON_PASSWORDS = {
    "password", "123456", "12345678", "qwerty", "letmein", "admin",
    "welcome", "iloveyou", "monkey", "dragon", "football", "abc123",
    "password1", "111111", "123123", "trustno1",
}

REPEATED_CHAR_PATTERN = re.compile(r"(.)\1{2,}")
SEQUENTIAL_DIGITS_PATTERN = re.compile(
    r"^(?:0123|1234|2345|3456|4567|5678|6789|9876|8765|7654|6543|5432|4321|3210)"
)


def score_password(password: str) -> tuple[int, str, list[str]]:
    """Returns (score 0-100, label, feedback). Never log or persist `password`."""
    if not password:
        return 0, "Enter a password above", []

    feedback: list[str] = []
    points = 0

    if len(password) >= 8:
        points += 20
    if len(password) >= 12:
        points += 20
    if len(password) >= 16:
        points += 10
    if len(password) < 8:
        feedback.append("Use at least 8 characters (12+ is much stronger).")

    has_lower = bool(re.search(r"[a-z]", password))
    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"[0-9]", password))
    has_symbol = bool(re.search(r"[^a-zA-Z0-9]", password))
    variety_count = sum([has_lower, has_upper, has_digit, has_symbol])
    points += variety_count * 10

    if not has_upper:
        feedback.append("Add an uppercase letter.")
    if not has_digit:
        feedback.append("Add a number.")
    if not has_symbol:
        feedback.append("Add a symbol (e.g. ! @ # $).")

    if REPEATED_CHAR_PATTERN.search(password):
        points -= 15
        feedback.append("Avoid repeating the same character three or more times.")

    if SEQUENTIAL_DIGITS_PATTERN.search(password):
        points -= 10
        feedback.append("Avoid sequential digits like 1234.")

    if password.lower() in COMMON_PASSWORDS:
        points = min(points, 15)
        feedback.append("This is one of the most commonly used passwords - avoid it entirely.")

    points = max(0, min(100, points))

    if points < 30:
        label = "Very Weak"
    elif points < 50:
        label = "Weak"
    elif points < 70:
        label = "Fair"
    elif points < 90:
        label = "Strong"
    else:
        label = "Very Strong"

    if not feedback:
        feedback.append("Looks good.")

    return points, label, feedback
