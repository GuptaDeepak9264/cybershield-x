/*
 * CyberShield X - password strength scoring.
 *
 * This is a rule-based scorer, not full entropy estimation (that's a
 * reasonable job for a library like zxcvbn, which we're deliberately not
 * pulling in for a single form field). It rewards length and character
 * variety, and penalizes the common weak patterns people actually use.
 *
 * FastAPI will expose the same checks as a POST endpoint in Milestone 3
 * for programmatic callers; this client-side copy exists purely so the
 * UI updates on every keystroke without a network round trip.
 */

const COMMON_PASSWORDS = new Set([
    "password", "123456", "12345678", "qwerty", "letmein", "admin",
    "welcome", "iloveyou", "monkey", "dragon", "football", "abc123",
    "password1", "111111", "123123", "trustno1",
]);

function scorePassword(pwd) {
    if (!pwd) {
        return { score: 0, label: "Enter a password above", feedback: [] };
    }

    const feedback = [];
    let points = 0;

    // Length is the single strongest predictor of crack resistance.
    if (pwd.length >= 8) points += 20;
    if (pwd.length >= 12) points += 20;
    if (pwd.length >= 16) points += 10;
    if (pwd.length < 8) feedback.push("Use at least 8 characters (12+ is much stronger).");

    const hasLower = /[a-z]/.test(pwd);
    const hasUpper = /[A-Z]/.test(pwd);
    const hasDigit = /[0-9]/.test(pwd);
    const hasSymbol = /[^a-zA-Z0-9]/.test(pwd);
    const varietyCount = [hasLower, hasUpper, hasDigit, hasSymbol].filter(Boolean).length;
    points += varietyCount * 10;

    if (!hasUpper) feedback.push("Add an uppercase letter.");
    if (!hasDigit) feedback.push("Add a number.");
    if (!hasSymbol) feedback.push("Add a symbol (e.g. ! @ # $).");

    if (/(.)\1{2,}/.test(pwd)) {
        points -= 15;
        feedback.push("Avoid repeating the same character three or more times.");
    }

    if (/^(?:0123|1234|2345|3456|4567|5678|6789|9876|8765|7654|6543|5432|4321|3210)/.test(pwd)) {
        points -= 10;
        feedback.push("Avoid sequential digits like 1234.");
    }

    if (COMMON_PASSWORDS.has(pwd.toLowerCase())) {
        points = Math.min(points, 15);
        feedback.push("This is one of the most commonly used passwords - avoid it entirely.");
    }

    points = Math.max(0, Math.min(100, points));

    let label;
    if (points < 30) label = "Very Weak";
    else if (points < 50) label = "Weak";
    else if (points < 70) label = "Fair";
    else if (points < 90) label = "Strong";
    else label = "Very Strong";

    if (feedback.length === 0) feedback.push("Looks good.");

    return { score: points, label, feedback };
}

document.addEventListener("DOMContentLoaded", () => {
    const input = document.getElementById("pwd-input");
    const bar = document.getElementById("pwd-bar");
    const label = document.getElementById("pwd-label");
    const feedbackList = document.getElementById("pwd-feedback");
    const toggle = document.getElementById("pwd-toggle");

    const colorForScore = (score) => {
        if (score < 30) return "bg-danger";
        if (score < 50) return "bg-warning";
        if (score < 70) return "bg-info";
        return "bg-success";
    };

    input.addEventListener("input", () => {
        const { score, label: text, feedback } = scorePassword(input.value);
        bar.style.width = `${score}%`;
        bar.className = `progress-bar ${colorForScore(score)}`;
        label.textContent = text;
        feedbackList.innerHTML = "";
        feedback.forEach((item) => {
            const li = document.createElement("li");
            li.textContent = item;
            feedbackList.appendChild(li);
        });
    });

    toggle.addEventListener("click", () => {
        const isPassword = input.type === "password";
        input.type = isPassword ? "text" : "password";
        toggle.textContent = isPassword ? "Hide" : "Show";
    });
});
