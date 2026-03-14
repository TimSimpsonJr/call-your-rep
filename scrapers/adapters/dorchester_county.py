"""Adapter for Dorchester County Council members.

Scrapes a Granicus-hosted page where members are listed in an HTML table
with columns: District | Representative | Phone | Email.
"""

import re

import requests
from bs4 import BeautifulSoup

from .base import BaseAdapter

USER_AGENT = "CallYourRep/1.0 (+https://github.com/TimSimpsonJr/call-your-rep)"


class DorchesterCountyAdapter(BaseAdapter):

    def fetch(self) -> str:
        url = self.config.get("url", self.url)
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        return resp.text

    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if not table:
            raise ValueError("No table found on Dorchester County council page")

        members = []
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 4:
                continue

            district = cells[0].get_text(strip=True)
            raw_name = cells[1].get_text(strip=True)
            phone = cells[2].get_text(strip=True)

            # Email: may be in mailto link or plain text
            email_link = cells[3].find("a", href=re.compile(r"^mailto:"))
            if email_link and email_link["href"].strip() != "mailto:":
                email = email_link["href"].replace("mailto:", "").strip()
            else:
                email = cells[3].get_text(strip=True)

            # Clean name: strip honorifics and title suffixes
            name = re.sub(r"^(Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+", "", raw_name)
            name = re.sub(r",\s*(Chairman|Vice[- ]?Chair(?:man)?)\s*$", "", name, flags=re.I)

            # Extract title from suffix or default
            title_match = re.search(r",\s*(Chairman|Vice[- ]?Chair(?:man)?)\s*$", raw_name, re.I)
            if title_match:
                title = f"{title_match.group(1)}, District {district}"
            else:
                title = f"Council Member, District {district}"

            members.append({
                "name": name.strip(),
                "title": title,
                "email": email,
                "phone": phone,
            })

        return members
