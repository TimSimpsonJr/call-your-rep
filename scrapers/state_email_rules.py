"""Per-state email conventions for backfilling missing emails from OpenStates.

When OpenStates data is missing an email address, the scraper can generate one
using the state's known email format. Generated emails are flagged with
"emailVerified": false so consumers know they're unverified.

Format placeholders:
    {first}  - lowercase first name
    {last}   - lowercase last name
    {first1} - first letter of first name (lowercase)
"""

STATE_EMAIL_RULES = {
    "SC": {
        "senate": {"domain": "scsenate.gov", "format": "{first}{last}"},
        "house": {"domain": "schouse.gov", "format": "{first}{last}"},
    },
}


def generate_email(state: str, chamber: str, first_name: str, last_name: str) -> str | None:
    """Generate an email address from state email rules.

    Returns the generated email or None if no rule exists for the state/chamber.
    """
    rules = STATE_EMAIL_RULES.get(state, {})
    chamber_rule = rules.get(chamber)
    if not chamber_rule:
        return None

    domain = chamber_rule["domain"]
    fmt = chamber_rule["format"]

    email = fmt.format(
        first=first_name.lower().replace(" ", ""),
        last=last_name.lower().replace(" ", ""),
        first1=first_name[0].lower() if first_name else "",
    )

    return f"{email}@{domain}"
