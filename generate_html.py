# file: lindholmen_lunch/generate_html.py

import json
import os
from jinja2 import Environment, FileSystemLoader
from datetime import datetime, timedelta, timezone
from pathlib import Path
from utils.annotate_food_types import annotate_file, load_keywords


def load_restaurant_links() -> dict:
    try:
        with open("data/restaurant_links.json", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("[WARN] restaurant_links.json missing or malformed, skipping links.")
        return {}

def generate_lunch_summary(day: str):
    data_path = f"data/lunch_data_{day}.json"
    if not os.path.exists(data_path):
        print(f"[WARN] No data file for {day}: {data_path}")
        return
    
    # Annotate food types in the data file
    annotate_file(data_path)

    with open(data_path, encoding="utf-8") as f:
        lunch_data = json.load(f)

    restaurant_links = load_restaurant_links()

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("summary_template.html")

    # CEST / Sweden local time (UTC+2)
    sweden_tz = timezone(timedelta(hours=2))
    today = datetime.now(sweden_tz).date()

    # Mark stale restaurants (last_scraped before today)
    for _, data in lunch_data.items():
        ts = data.get("last_scraped")
        is_stale = True
        if ts:
            try:
                scraped_dt = datetime.strptime(ts, "%Y-%m-%d")
                is_stale = scraped_dt.date() < today
            except ValueError:
                is_stale = True
        data["is_stale"] = is_stale

    food_tags = load_keywords()
    food_tag_groups = {}
    for tag, info in food_tags.items():
        prio = info.get("priority", 100)
        if prio not in food_tag_groups:
            food_tag_groups[prio] = []
        food_tag_groups[prio].append((tag, info["emoji"]))

    emoji_map = {tag: data["emoji"] for tag, data in food_tags.items()}

    output_html = template.render(
        day=day.capitalize(),
        lunch_data=lunch_data,
        emoji_map=emoji_map,
        restaurant_links=restaurant_links,
        last_updated=datetime.now(sweden_tz).strftime("%Y-%m-%d %H:%M"),
        food_tag_groups=food_tag_groups
    )

    os.makedirs("docs", exist_ok=True)
    output_path = f"docs/lunch_{day}.html"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_html)

    print(f"[INFO] Generated HTML summary for {day}: {output_path}")


def generate_index_page():
    output_dir = Path("docs")
    output_dir.mkdir(exist_ok=True)
    weekdays = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    available_days = [day for day in weekdays if (output_dir / f"lunch_{day}.html").exists()]
    env = Environment(loader=FileSystemLoader("templates"))
    html = env.get_template("index_template.html").render(available_days=available_days)
    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"[INFO] Generated daily menu redirect: {index_path}")
