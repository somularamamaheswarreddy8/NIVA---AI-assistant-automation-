import urllib.request
import re
import json

req = urllib.request.Request(
    'https://www.youtube.com/results?search_query=believer',
    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
)
try:
    with urllib.request.urlopen(req, timeout=5.0) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        matches = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"([^"]+)"\}', html)
        print("Matches found:", len(matches))
        for vid, title in matches[:5]:
            print(f"ID: {vid} | Title: {title}")
except Exception as e:
    print("Error:", e)
