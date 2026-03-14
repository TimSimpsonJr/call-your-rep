"""Adapter for Kershaw County Council members.

Scrapes a Granicus-hosted page where member data is in plain <p> tags
with <br>-separated fields: name, email, phone, term dates. Titles
appear in <strong> tags in preceding paragraphs.
"""

import re

import requests
from bs4 import BeautifulSoup

from .base import BaseAdapter

USER_AGENT = "CallYourRep/1.0 (+https://github.com/TimSimpsonJr/call-your-rep)"

EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.\w+")
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.\-]*\d{3}[\s.\-]*\d{4}")


class KershawCountyAdapter(BaseAdapter):

    def fetch(self) -> str:
        url = self.config.get("url", self.url)
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        return resp.text

    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        content = soup.find("div", class_="content_area")
        if not content:
            content = soup.find("div", class_="right_col") or soup

        members = []
        current_title = None

        for p in content.find_all("p"):
            # Check for title in <strong> tags
            strong = p.find("strong")
            if strong:
                strong_text = strong.get_text(strip=True)
                if re.search(r"(chairman|council\s*member|district)", strong_text, re.I):
                    current_title = strong_text
                    continue

            # Get all text lines from this paragraph (split on <br>)
            text = p.get_text(separator="\n", strip=True)
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            if not lines:
                continue

            # Look for a paragraph with both a name and an email
            email_match = None
            phone_match = None
            name = None

            for line in lines:
                if EMAIL_RE.search(line) and not email_match:
                    email_match = EMAIL_RE.search(line).group(0)
                elif PHONE_RE.search(line) and not phone_match:
                    phone_match = PHONE_RE.search(line).group(0)
                elif not name and not re.search(r"(term|expires|\d{2}/\d{2})", line, re.I):
                    name = line

            if name and (email_match or phone_match):
                members.append({
                    "name": name,
                    "title": current_title or "Council Member",
                    "email": email_match or "",
                    "phone": phone_match or "",
                })
                current_title = None

        return members
