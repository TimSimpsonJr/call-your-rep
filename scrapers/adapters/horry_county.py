"""Adapter for Horry County Council members.

Scrapes a Granicus-hosted page with custom CSS classes: .council-member
and .council-info. Name and title are colon-separated in the first div.
"""

import re

import requests
from bs4 import BeautifulSoup

from .base import BaseAdapter

USER_AGENT = "CallYourRep/1.0 (+https://github.com/TimSimpsonJr/call-your-rep)"


class HorryCountyAdapter(BaseAdapter):

    def fetch(self) -> str:
        url = self.config.get("url", self.url)
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        return resp.text

    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        members = []

        for card in soup.find_all("div", class_="council-member"):
            info = card.find("div", class_="council-info")
            if not info:
                continue

            # First div in council-info has "Name: Title" format
            divs = info.find_all("div", recursive=False)
            if not divs:
                continue

            name_title_text = divs[0].get_text(strip=True)
            if ":" in name_title_text:
                name, title = name_title_text.split(":", 1)
                name = name.strip()
                title = title.strip()
                # "District N" -> "Council Member, District N"
                if re.match(r"^District\s+\d+$", title, re.I):
                    title = f"Council Member, {title}"
            else:
                name = name_title_text
                title = "Council Member"

            # Skip non-member entries (e.g., general info cards)
            if not name or name.lower() in ("county council", "horry county"):
                continue

            # Email from mailto link
            email = ""
            email_link = info.find("a", href=re.compile(r"^mailto:"))
            if email_link:
                email = email_link["href"].replace("mailto:", "").strip()

            # Phone from tel link
            phone = ""
            phone_link = info.find("a", href=re.compile(r"^tel:"))
            if phone_link:
                phone = phone_link.get_text(strip=True)

            members.append({
                "name": name,
                "title": title,
                "email": email,
                "phone": phone,
            })

        return members
