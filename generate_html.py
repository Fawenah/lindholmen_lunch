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

    weekday_order = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    weekday_labels = {
        "monday": "Måndag",
        "tuesday": "Tisdag",
        "wednesday": "Onsdag",
        "thursday": "Torsdag",
        "friday": "Fredag"
    }

    lunch_files = {f.stem.replace("lunch_", ""): f for f in output_dir.glob("lunch_*.html")}
    ordered_links = [(day, lunch_files[day]) for day in weekday_order if day in lunch_files]

    html = """<html><head>
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-LMDT71XZ0C"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-LMDT71XZ0C');
    </script>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7499028717075061"
     crossorigin="anonymous"></script>
    <meta charset='utf-8'>
    <meta name="google-site-verification" content="iUNSsOQ8Uw21911zTxrbq0FNyaY7uwQu6iq8XffofsA" />
    <title>Dagens lunch på Lindholmen</title>
    <meta name="description" content="Dagens lunch från restauranger på Lindholmen – uppdateras dagligen." />
    <style>
    body {
        font-family: Arial, sans-serif;
        background: #f8f8f8;
        padding: 20px;
        max-width: 80%;
    }
    h1 { color: #004d66; }
    .button-container {
        margin-top: 30px;
        display: flex;
        flex-direction: column;
        gap: 15px;
    }
    .weekday-button {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #004d66;
        color: white;
        padding: 15px;
        border-radius: 8px;
        font-size: 18px;
        text-decoration: none;
        font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: background 0.2s ease;
    }
    .weekday-button:hover { background: #006080; }
    .timestamp {
        font-size: 13px;
        font-weight: normal;
        color: #ccc;
    }
    .restaurant-list {
        margin-top: 50px;
    }
    .restaurant-list h2 {
        font-size: 20px;
        color: #004d66;
        margin-bottom: 15px;
    }
    .restaurant-entry {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px solid #eee;
    }
    .restaurant-name {
        font-weight: bold;
        font-size: 16px;
        color: #333;
    }
    .restaurant-links a {
        text-decoration: none;
        font-size: 1.2em;
        margin-left: 10px;
        color: #004d66;
    }
    .restaurant-links a:hover {
        text-decoration: underline;
        color: #006080;
    }
    footer.footer {
        margin-top: 50px;
        padding-top: 20px;
        border-top: 1px solid #ccc;
        font-size: 14px;
        color: #666;
    }
    footer.footer a {
        color: #004d66;
        text-decoration: none;
    }
    footer.footer a:hover {
        text-decoration: underline;
    }
    </style>
    </head><body>
    <h1>Dagens lunch på Lindholmen</h1>
    <p>Här hittar du dagens lunchmenyer från restauranger på Lindholmen – uppdateras varje vardag med aktuella menyer från lokala favoriter som Kooperativet, District One, Bombay Bistro, Masala Kitchen och många fler.</p>
    <div class="button-container">
    """

    for day, file in ordered_links:
        label = weekday_labels[day]
        ts = datetime.fromtimestamp(file.stat().st_mtime, tz=timezone(timedelta(hours=2))).strftime("%Y-%m-%d %H:%M")
        html += f"""
        <a class="weekday-button" href="{file.name}">
            <span>{label}</span>
            <span class="timestamp">Last updated: {ts}</span>
        </a>
        """

    html += """
    </div>
    <hr>
    <div class="restaurant-list">
        <h2>Restauranger</h2>
    """

    restaurant_links = load_restaurant_links()
    if not restaurant_links:
        print("[WARN] No restaurant links found.")
        return

    for name in sorted(restaurant_links.keys()):
        links = restaurant_links[name]
        html += f"""
        <div class="restaurant-entry">
            <span class="restaurant-name">{name}</span>
            <span class="restaurant-links">"""
        if links.get("url"):
            html += f'<a href="{links["url"]}" target="_blank" title="Hemsida">🔗</a>'
        if links.get("map"):
            html += f'<a href="{links["map"]}" target="_blank" title="Google Maps">🗺️</a>'
        html += "</span></div>"

    html += """
    </div>
    """
    html += """
    <hr>
    <footer class="footer">
        <p>Denna lunchsammanställning är öppen källkod – <a href="https://github.com/Fawenah/lindholmen_lunch" target="_blank">GitHub - Lindholmen Lunch</a></p>
        <p>Har du frågor, feedback eller saknar din favoritrestaurang? Öppna ett issue, pull request, kontakta mig via GitHub eller via <a href="mailto:fawenah@gmail.com">fawenah@gmail.com</a>.</p>
    </footer>
    <footer style="text-align:center; font-size:13px; color:#888; margin-top:40px;">
        Lindholmen Lunch – <a href="privacy.html" style="color:#004d66;">Integritetspolicy</a>
    </footer>
    </body></html>
    """


    index_path = output_dir / "index.html"
    index_path.write_text(html, encoding="utf-8")
    print(f"[INFO] Generated weekly index page: {index_path}")
