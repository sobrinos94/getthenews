import csv
import json
import datetime
import requests
from bs4 import BeautifulSoup
from requests_html import HTMLSession
from urllib.parse import urlparse
from pathlib import Path

# Initialize session for JS rendering
session = HTMLSession()

# Paths
BASE_DIR = Path(__file__).parent.parent
INPUT_CSV = BASE_DIR / "discovery" / "output" / f"articles_{datetime.date.today().isoformat()}.csv"
OUTPUT_FILE = BASE_DIR / "discovery" / "output" / f"content_{datetime.date.today().isoformat()}.jsonl"


def fetch_content_nos(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.select_one('h1').get_text(strip=True) if soup.select_one('h1') else ''
    lead_elem = soup.select_one('.article__intro')
    lead = lead_elem.get_text(strip=True) if lead_elem else ''
    body = '\n'.join(p.get_text(strip=True) for p in soup.select('.article__body p'))
    author_elem = soup.select_one('.article__meta-author')
    author = author_elem.get_text(strip=True) if author_elem else ''
    tags = [tag.get_text(strip=True) for tag in soup.select('.article__tag')]
    return title, lead, body, author, tags


def fetch_content_nu(url):
    """
    Use HTMLSession to render JS and bypass privacy gate for NU.nl; fallback gracefully on errors.
    """
    try:
        # Render page with JS
        r = session.get(url)
        r.html.render(timeout=20, retries=1, sleep=2)
        html = r.ht

def fetch_content_generic(html):
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.get_text(strip=True) if soup.title else ''
    body = ' '.join(p.get_text(strip=True) for p in soup.find_all('p'))
    return title, '', body, '', []


def main():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INPUT_CSV, newline='', encoding='utf-8') as csvfile, \
         open(OUTPUT_FILE, 'w', encoding='utf-8') as jsonlfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            url = row.get('url', '')
            source = row.get('source', '').upper()

            # Filter Telegraaf to only main-domain news
            if source == 'TELEGRAAF':
                parsed = urlparse(url)
                if parsed.netloc not in ('www.telegraaf.nl', 'telegraaf.nl') or not parsed.path.startswith('/nieuws/'):
                    continue

            try:
                if source == 'NOS':
                    # NOS: use simple GET
                    resp = requests.get(url)
                    resp.raise_for_status()
                    title, lead, body, author, tags = fetch_content_nos(resp.text)
                elif source == 'NU.NL':
                    # NU.nl: use JS-rendering session
                    title, lead, body, author, tags = fetch_content_nu(url)
                else:
                    # Fallback for other sources
                    resp = requests.get(url)
                    resp.raise_for_status()
                    title, lead, body, author, tags = fetch_content_generic(resp.text)

                entry = {**row,
                         'title': title,
                         'lead': lead,
                         'body': body,
                         'author': author,
                         'tags': tags}
                jsonlfile.write(json.dumps(entry, ensure_ascii=False) + '\n')

            except Exception as e:
                print(f"Error fetching content for {url}: {e}")

if __name__ == '__main__':
    main()
