import json
import json

def load_keywords():
    with open("data/food_tags.json", encoding="utf-8") as f:
        return json.load(f)

def annotate_file(filename: str):
    with open(filename, encoding="utf-8") as f:
        data = json.load(f)

    tag_data = load_keywords()

    for scraper_name, menu in data.items():
        for item in menu.get("items", []):
            text = " ".join([
                item.get("name", ""),
                item.get("description", ""),
                item.get("category", "")
            ]).lower()

            matched_tags = []
            for tag, info in tag_data.items():
                if any(kw.lower() in text for kw in info["keywords"]):
                    matched_tags.append((info.get("priority", 100), tag))

            # Sort by priority and assign unique tags
            unique_tags = []
            seen = set()
            for _, tag in sorted(matched_tags):
                if tag not in seen:
                    unique_tags.append(tag)
                    seen.add(tag)

            item["tags"] = unique_tags

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"[INFO] Annotated emoji tags in {filename} (prioritized & fuzzy match)")

