"""Map a character to its side in the galaxy, which drives the page's accent color."""

# key -> (Hebrew label, accent color)
SIDES = {
    "sith": ("הצד האפל · סית'", "#FF3B3B"),
    "jedi": ("מסדר הג'דיי", "#4BB3FD"),
    "rebel": ("המורדים", "#FF8C3A"),
    "underworld": ("העולם התחתון", "#3FE08A"),
    "separatist": ("הבדלנים", "#B57BFF"),
    "empire": ("האימפריה", "#B8C7DB"),
    "republic": ("הרפובליקה", "#FFD23F"),
    "droid": ("דרואידים", "#2EE6D6"),
    "neutral": ("תושבי הגלקסיה", "#E2B77A"),
}

# Checked in order: the first side whose keyword appears in the character's affiliations wins.
# Rebels come before the underworld and the Empire, so characters who switched sides
# (Han Solo, Finn, Bail Organa...) are shown with the side they are remembered for.
_SIDE_KEYWORDS = [
    ("sith", ["sith"]),
    ("jedi", ["jedi"]),
    ("rebel", ["alliance to restore", "rebel", "resistance", "new republic"]),
    ("underworld", ["criminal", "syndicate", "shadow collective", "hutt", "bounty"]),
    ("separatist", ["confederacy", "separatist", "trade federation", "techno union"]),
    # Clear Imperial roles first; Republic politicians who merely continued under the Empire stay Republic
    ("empire", ["first order", "imperial high command", "imperial navy", "imperial officer",
                "imperial ruling council", "battle station"]),
    ("republic", ["galactic republic", "naboo", "gungan", "senate", "republic"]),
    ("empire", ["galactic empire"]),
]


def get_side(char):
    """Return (side_key, hebrew_label, color) for a character from the Star Wars API."""
    affiliations = " | ".join(char.get("affiliations") or []).lower()
    side = next(
        (key for key, words in _SIDE_KEYWORDS if any(w in affiliations for w in words)),
        "droid" if char.get("species") == "droid" else "neutral",
    )
    label, color = SIDES[side]
    return side, label, color
