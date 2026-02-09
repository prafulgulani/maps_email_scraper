import pandas as pd
import csv
import os
from playwright.sync_api import sync_playwright
import re
import time


INPUT_FILE = "mumbai.csv"
OUTPUT_FILE = "mumbai_emails_new.csv"

if not os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["index", "name",
                        "rating", "ratings_count", 
                        "website", "phone","emails", 
                        "instagram","facebook","linkedin","twitter","youtube","whatsapp",])

SOCIAL_PATTERNS = {
    "instagram": r"https?://(?:www\.)?instagram\.com/[^\s\"'>]+",
    "facebook":  r"https?://(?:www\.)?facebook\.com/[^\s\"'>]+",
    "linkedin":  r"https?://(?:www\.)?linkedin\.com/[^\s\"'>]+",
    "twitter":   r"https?://(?:www\.)?(?:twitter|x)\.com/[^\s\"'>]+",
    "youtube":   r"https?://(?:www\.)?youtube\.com/[^\s\"'>]+",
    "whatsapp":        r"https?://(?:wa\.me|api\.whatsapp\.com)/[^\s\"'>]+",
}

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
)

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico")

processed = set()

if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            processed.add(int(row["index"]))

def clean_emails(email_list):
    if not email_list:
        return ""

    clean = set()

    for e in email_list:
        if not e:
            continue

        e = str(e).strip().lower()

        # remove brackets or junk characters
        e = e.strip("<>\"' ")

        # skip images or files
        if e.endswith(IMAGE_EXTENSIONS):
            continue

        # final strict validation (safety)
        if EMAIL_REGEX.fullmatch(e):
            clean.add(e)

    return ";".join(clean)

def find_contacts_playwright(page, base_url):
    paths = [
        "",
        "/contact", "/contact-us", "/contactus", "/contact.html",
        "/about", "/about-us",
        "/get-in-touch", "/reach-us", "/support"
    ]

    found = set()
    socials_found = {k: set() for k in SOCIAL_PATTERNS}

    for path in paths:
        try:
            url = base_url.rstrip("/") + path

            page.goto(url, timeout=30000, wait_until="networkidle")

            # scroll fully (important for lazy load footers)
            page.mouse.wheel(0, 10000)

            # small wait for JS render
            page.wait_for_timeout(1500)

            content = page.content()

            # normal emails
            found.update(EMAIL_REGEX.findall(content))

            # also extract mailto links
            links = page.locator('a[href^="mailto:"]').all()
            for link in links:
                href = link.get_attribute("href")
                if href:
                    found.add(href.replace("mailto:", "").split("?")[0])

            # ---- socials ----
            for key, pattern in SOCIAL_PATTERNS.items():
                links = re.findall(pattern, content)
                socials_found[key].update(links)

        except:
            continue

    socials_clean = {
        k: ";".join(sorted(v)) if v else ""
        for k, v in socials_found.items()
    }

    return clean_emails(found), socials_clean


def parse_rating(rating_str):
    if pd.isna(rating_str) or rating_str == "No reviews":
        return None, 0

    rating_str = str(rating_str)

    match = re.match(r"([\d.]+)\(([\d,]+)\)", rating_str)
    if match:
        rating = float(match.group(1))
        count = int(match.group(2).replace(",", ""))
        return rating, count

    return None, 0







df = pd.read_csv(INPUT_FILE)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)

        for row in df.itertuples(index=True):
            idx = row.Index
            if idx in processed:
                continue

            name = row.name
            rating, ratings_count = parse_rating(row.address)
            phone = row.phone
            website = row.website

            print(f"🔍 {idx} | {name}")
            emails = ""
            socials = {k: "" for k in SOCIAL_PATTERNS}

            if isinstance(website, str) and website.startswith("http"):
                emails, socials = find_contacts_playwright(page, website)
            time.sleep(2)
            writer.writerow([idx, name, rating, ratings_count, website, phone, emails,
                socials["instagram"],
                socials["facebook"],
                socials["linkedin"],
                socials["twitter"],
                socials["youtube"],
                socials["whatsapp"],])
            f.flush()

            print("   ➜", emails)

    page.close()
    browser.close()