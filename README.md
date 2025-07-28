# Web-Scrapping

# ♻️ Earth911 Recycling Facility Scraper

This project is a Python-based web scraper that extracts recycling center data from Earth911’s public Recycling Center Search tool using Selenium.

## 🌐 Website Used

> https://search.earth911.com/?what=Electronics&where=10001&list_filter=all&max_distance=100&country=US

The scraper fetches information for facilities that accept **Electronics** near **ZIP Code 10001 (New York, NY)** within a **100-mile radius**.

---

## 🧾 Output Format (CSV)

The script extracts at least 3 recycling facilities with the following fields:

| Field               | Description                                     |
|--------------------|-------------------------------------------------|
| `business_name`     | Official name of the recycling center           |
| `last_update_date`  | Last time the data was updated on Earth911      |
| `street_address`    | Physical address of the facility                |
| `materials_accepted`| List of materials accepted at the location      |

Example:
```csv
business_name,last_update_date,street_address,materials_accepted
Green Earth Recyclers,2023-11-04,123 5th Ave, New York, NY 10001,Computers, Smartphones, Lithium-ion Batteries
