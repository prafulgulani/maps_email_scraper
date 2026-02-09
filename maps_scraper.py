from playwright.sync_api import sync_playwright
import time
import csv

def generate_grid(lat_start, lat_end, lng_start, lng_end, step=0.05):
    points = []
    idx = 0

    lat_steps = int((lat_end - lat_start) / step) + 1
    lng_steps = int((lng_end - lng_start) / step) + 1

    for i in range(lat_steps):
        lat = round(lat_start + i * step, 5)
        for j in range(lng_steps):
            lng = round(lng_start + j * step, 5)
            points.append((lat, lng))
            idx += 1

    return points

def scrape_google_maps(query, grid, zoom=14, scrolls=16, cooldown=5):
    results = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.set_default_timeout(60000)

        for lat, lng in grid:
            print(f"\n🔍 Searching '{query}' at {lat}, {lng}")

            url = f"https://www.google.com/maps/search/{query}/@{lat},{lng},{zoom}z"
            page.goto(url)

            try:
                page.wait_for_selector('div[role="feed"]', timeout=15000)
            except:
                print("❌ No feed found, skipping")
                continue

            feed = page.locator('div[role="feed"]')

            prev_count = 0
            for _ in range(scrolls):
                cards = feed.locator('div[role="article"]')
                count = cards.count()

                if count == prev_count:
                    page.mouse.wheel(0, 3000)
                    time.sleep(2)
                    continue

                for i in range(prev_count, count):
                    card = cards.nth(i)

                    name = card.locator('div.qBF1Pd').first.text_content()
                    if not name:
                        continue

                    rating = (
                        card.locator('div.W4Efsd').first.text_content()
                        if card.locator('div.W4Efsd').count()
                        else None
                    )

                    key = name.strip()
                    if key in seen:
                        continue
                    seen.add(key)

                    phone = None
                    website = None
                    
                    try:
                        card.click()
                        time.sleep(2)

                        phone_button = page.locator('button[data-item-id^="phone"]')

                        if phone_button.count():
                            # Get the aria-label
                            raw_phone = phone_button.first.get_attribute("aria-label")
                            
                            if raw_phone:
                                # Remove the "Phone: " prefix 
                                phone = raw_phone.replace("Phone:", "").strip()
                            else:
                                # Just in case aria-label is missing, clean the text manually
                                phone = phone_button.first.text_content().replace("", "").strip()

                        if page.locator('a[data-item-id="authority"]').count():
                            website = page.locator('a[data-item-id="authority"]').first.get_attribute("href")

                    except Exception:
                        pass

                    results.append({
                        "name": name.strip(),
                        "rating": rating.strip() if rating else None,
                        "phone": phone,
                        "website": website
                    })
                prev_count = count
                page.mouse.wheel(0, 3000)
                time.sleep(2)

            time.sleep(cooldown)

        browser.close()

    print(f"\n✅ Total '{query}' collected:", len(results))
    return results


def save_to_csv(filename, results):
    if not results:
        print("⚠️ No data to save")
        return

    fieldnames = results[0].keys()

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(results)

    print(f"📁 Saved {len(results)} records to {filename}")






# mumbai = generate_grid(18.88, 19.28, 72.77, 73.02, step=0.1)

# results = scrape_google_maps(
#     query="study abroad consultant",
#     grid=mumbai
# )

# save_to_csv("mumbai.csv", results)