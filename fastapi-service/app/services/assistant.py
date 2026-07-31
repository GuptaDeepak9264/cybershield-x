"""
AI Security Assistant.

Two genuinely working modes, not one real path and one fake stub:

1. "llm"      - if OPENAI_API_KEY is configured, the message is sent to
                OpenAI's chat completions API with a cybersecurity-focused
                system prompt.
2. "fallback" - if no key is configured, a small keyword-matched knowledge
                base answers common cybersecurity questions directly. This
                keeps the milestone runnable with zero paid dependencies,
                and the response always says which mode produced it so
                nobody mistakes canned advice for a live model.
"""

from ..config import get_settings

_FALLBACK_KB: list[tuple[tuple[str, ...], str]] = [
    (
        ("phishing",),
        "Phishing emails try to trick you into revealing credentials or "
        "clicking a malicious link. Check the sender's actual email address "
        "(not just the display name), hover over links before clicking, and "
        "be suspicious of urgent language ('your account will be closed'). "
        "When in doubt, go to the site directly instead of clicking the link.",
    ),
    (
        ("password", "passwords"),
        "Strong passwords are long (12+ characters), unique per site, and "
        "not reused. A password manager is the single biggest upgrade most "
        "people can make - it removes the temptation to reuse passwords. "
        "Try the Password Checker in your dashboard to test one.",
    ),
    (
        ("ransomware",),
        "Ransomware encrypts your files and demands payment to unlock them. "
        "The best defenses are offline/immutable backups (so you can restore "
        "without paying), keeping software patched, and not opening "
        "unexpected attachments. Never pay first-instinct - contact your "
        "IT/security team.",
    ),
    (
        ("mfa", "2fa", "two-factor", "two factor", "multi-factor"),
        "Multi-factor authentication (MFA) requires a second proof of "
        "identity beyond your password - usually a code from an app or a "
        "hardware key. Even if a password leaks, MFA blocks most account "
        "takeovers. Prefer an authenticator app or hardware key over SMS "
        "codes, which can be intercepted via SIM-swapping.",
    ),
    (
        ("vpn",),
        "A VPN encrypts traffic between your device and the VPN provider, "
        "which is useful on untrusted networks (public wifi) and hides your "
        "traffic from your ISP. It does NOT make you anonymous online, and "
        "it doesn't protect against phishing or malware you download "
        "yourself.",
    ),
    (
        ("firewall",),
        "A firewall filters network traffic based on rules - blocking "
        "unsolicited inbound connections is its most important job on a "
        "personal device. Most operating systems ship one enabled by "
        "default; the main mistake is disabling it 'to make something work' "
        "and forgetting to re-enable it.",
    ),
    (
        ("malware", "virus"),
        "Malware is any software designed to harm or exploit a system - "
        "viruses, trojans, spyware, and ransomware are all subtypes. "
        "Avoid pirated software and cracked installers (a common delivery "
        "vector), keep your OS patched, and use the file scanner here "
        "before opening anything you weren't expecting.",
    ),
]

_DEFAULT_FALLBACK_REPLY = (
    "I can help with cybersecurity basics - try asking about phishing, "
    "passwords, MFA, VPNs, firewalls, malware, or ransomware. "
    "(Running in fallback mode: no LLM provider is configured, so this is "
    "a rule-based answer, not a generated one.)"
)


def _fallback_reply(message: str) -> str:
    lowered = message.lower()
    for keywords, reply in _FALLBACK_KB:
        if any(keyword in lowered for keyword in keywords):
            return reply
    return _DEFAULT_FALLBACK_REPLY


def _llm_reply(message: str) -> str:
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the CyberShield X Security Assistant, embedded in a "
                    "student cybersecurity training dashboard. Answer clearly and "
                    "concisely, stay strictly within cybersecurity/infosec topics, "
                    "and decline unrelated requests by redirecting to the topic."
                ),
            },
            {"role": "user", "content": message},
        ],
        max_tokens=400,
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def get_assistant_reply(message: str) -> tuple[str, str]:
    """Returns (reply, mode)."""
    settings = get_settings()
    if not settings.OPENAI_API_KEY:
        return _fallback_reply(message), "fallback"

    try:
        return _llm_reply(message), "llm"
    except Exception:
        # A live provider outage shouldn't 500 the endpoint - degrade to
        # the same fallback a from-scratch deployment would use.
        return _fallback_reply(message), "fallback"
