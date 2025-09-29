import csv
import datetime
import requests
from bs4 import BeautifulSoup
import feedparser
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
SOURCES_CSV = BASE_DIR / "discovery" / "sources.csv"
OUTPUT_DIR = BASE_DIR / "discovery" / "output"


def fetch_rss(source_name, url):
    """
    Haal artikelen uit een RSS-feed met feedparser.
    Retourneert een lijst van dicts met source, url, date_found, date_published, time_published.
    """
    feed = feedparser.parse(url)
    articles = []
    for entry in feed.entries:
        link = entry.link
        date_published = ''
        time_published = ''
        if 'published_parsed' in entry and entry.published_parsed:
            t = entry.published_parsed
            dt = datetime.datetime(
                t.tm_year, t.tm_mon, t.tm_mday,
                t.tm_hour, t.tm_min, t.tm_sec
            )
            iso = dt.isoformat()
            date_published, time_published = iso.split('T')
        articles.append({
            'source': source_name,
            'url': link,
            'date_found': datetime.date.today().isoformat(),
            'date_published': date_published,
            'time_published': time_published
        })
    return articles


def fetch_html(source_name, url):
    """
    Scrape een standaard nieuws-HTML-pagina voor links.
    Pas indien nodig de CSS-selector aan per site.
    """
    resp = requests.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, 'html.parser')
    articles = []
    today = datetime.date.today().isoformat()
    for a in soup.select('a'):
        link = a.get('href')
        if link and link.startswith('http'):
            articles.append({
                'source': source_name,
                'url': link,
                'date_found': today,
                'date_published': '',  # geen datum beschikbaar
                'time_published': ''    # geen tijd beschikbaar
            })
    return articles


def main():
    # Zorg dat outputmap bestaat
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    today_str = datetime.date.today().isoformat()
    output_file = OUTPUT_DIR / f"articles_{today_str}.csv"

    # Lees bronspecificaties
    with open(SOURCES_CSV, newline='', encoding='utf-8') as src_file:
        reader = csv.DictReader(src_file)
        all_articles = []

        for row in reader:
            source = row['source']
            url = row['url']
            type_ = row['type'].strip().upper()
            try:
                if type_ == 'RSS':
                    all_articles.extend(fetch_rss(source, url))
                elif type_ in ('HTML', 'HTML/SITE'):
                    all_articles.extend(fetch_html(source, url))
                else:
                    print(f"Onbekend type voor {source}: {type_}")
            except Exception as e:
                print(f"Fout bij ophalen {source} ({url}): {e}")

    # Schrijf CSV met extra kolom voor tijd
    with open(output_file, 'w', newline='', encoding='utf-8') as out_file:
        writer = csv.DictWriter(
            out_file,
            fieldnames=['source', 'url', 'date_found', 'date_published', 'time_published']
        )
        writer.writeheader()
        for art in all_articles:
            writer.writerow(art)

    print(f"Generated: {output_file}")


if __name__ == '__main__':
    main()