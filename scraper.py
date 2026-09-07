import json
import re
from bs4 import BeautifulSoup
import requests


def scrape_specific_veco_post():
    url = "https://www.visayanelectric.com/post/service-interruption-september-6-12-2026"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        interruptions = []

        content_container = (
            soup.find("div", class_="post-content")
            or soup.find("article")
            or soup
        )

        # Target the smallest distinct structural units (like table rows or paragraphs) 
        # to avoid capturing nested wrappers that duplicate records.
        containers = content_container.find_all(["tr", "p", "div"])
        if not containers:
            containers = [content_container]

        current_date = "Scheduled Interruption"

        for container in containers:
            text = container.get_text(" ", strip=True)
            text = re.sub(r"\s+", " ", text)

            # Check if a date header is present in this block
            date_match = re.search(
                r"((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\s*(?:\([A-Za-z]+\))?)",
                text,
            )
            if date_match:
                current_date = date_match.group(1).strip()

            # Process only if it explicitly contains schedule identifiers
            if "Time:" in text and ("Purpose:" in text or "Areas Affected:" in text):
                time_match = re.search(
                    r"Time:\s*(.*?)(?=\s*Purpose:|\s*Areas Affected:|\s*Map:|$)",
                    text,
                    re.IGNORECASE,
                )
                purpose_match = re.search(
                    r"Purpose:\s*(.*?)(?=\s*Areas Affected:|\s*Time:|\s*Map:|$)",
                    text,
                    re.IGNORECASE,
                )
                areas_match = re.search(
                    r"Areas Affected:\s*(.*?)(?=\s*Time:|\s*Purpose:|\s*Map:|\s*(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}|$)",
                    text,
                    re.IGNORECASE,
                )

                time_val = time_match.group(1).strip() if time_match else ""
                purpose_val = purpose_match.group(1).strip() if purpose_match else ""
                areas_val = areas_match.group(1).strip() if areas_match else ""

                if areas_val.endswith("Map:"):
                    areas_val = areas_val[:-4].strip()

                # Extract map image specifically tied to this schedule element block
                map_url = ""
                img = container.find("img")
                if not img:
                    # Check parent/sibling scope if the image is structured right next to it
                    parent = container.parent
                    if parent:
                        img = parent.find("img")

                if img:
                    src = img.get("src") or img.get("data-src")
                    if src:
                        if src.startswith("/"):
                            src = "https://www.visayanelectric.com" + src
                        if "static.wixstatic.com/media" in src or "wixpress.com" in src:
                            if "/v1/fill/" in src:
                                src = re.sub(r"/v1/fill/.*?", "/v1/fit/w_800,h_800,q_90/", src)
                        map_url = src

                if time_val or purpose_val or areas_val:
                    entry = {
                        "date": current_date,
                        "time": time_val,
                        "purpose": purpose_val,
                        "areas": areas_val,
                        "map_image": map_url,
                    }
                    
                    # Prevent duplicate entries by checking both exact match and unique time+areas combination
                    is_duplicate = False
                    for existing in interruptions:
                        if existing["time"] == time_val and existing["areas"] == areas_val and existing["date"] == current_date:
                            is_duplicate = True
                            # If existing lacks a map image but the new one found it, update it
                            if not existing["map_image"] and map_url:
                                existing["map_image"] = map_url
                            break

                    if not is_duplicate and entry not in interruptions:
                        interruptions.append(entry)

        data = {
            "source_url": url,
            "total_schedules": len(interruptions),
            "interruptions": interruptions,
        }

        with open("interruptions.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(
            f"Successfully scraped and accurately mapped {len(interruptions)}"
            " unique schedules without duplication!"
        )

    except Exception as e:
        print(f"Error scraping the VECO link: {e}")


if __name__ == "__main__":
    scrape_specific_veco_post()