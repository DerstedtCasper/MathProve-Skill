"""Lightweight citation retriever (arXiv/Wikipedia)."""
import argparse
import json
import urllib.parse
import urllib.request

ARXIV_API = "http://export.arxiv.org/api/query?search_query=all:{}&max_results=2"
WIKI_API = "https://en.wikipedia.org/w/api.php?action=query&list=search&utf8=&format=json&srsearch={}"


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=8) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def query_arxiv(q: str) -> list[dict]:
    url = ARXIV_API.format(urllib.parse.quote(q))
    text = fetch(url)
    items = []
    for entry in text.split("<entry>")[1:3]:
        try:
            title = entry.split("<title>")[1].split("</title>")[0].strip()
            link = entry.split("<id>")[1].split("</id>")[0].strip()
            items.append({"source": "arXiv", "title": title, "url": link})
        except Exception:  # noqa: BLE001
            continue
    return items


def query_wiki(q: str) -> list[dict]:
    url = WIKI_API.format(urllib.parse.quote(q))
    text = fetch(url)
    data = json.loads(text)
    results = data.get("query", {}).get("search", [])
    if not results:
        return []
    best = results[0]
    title = best.get("title", "")
    snippet = best.get("snippet", "")
    page_url = "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
    return [{"source": "Wikipedia", "title": title, "summary": snippet, "url": page_url}]


def main() -> None:
    parser = argparse.ArgumentParser(description="retrieve citations")
    parser.add_argument("query", nargs="+", help="search query")
    args = parser.parse_args()
    q = " ".join(args.query)
    items = []
    try:
        items.extend(query_arxiv(q))
    except Exception:  # noqa: BLE001
        pass
    try:
        items.extend(query_wiki(q))
    except Exception:  # noqa: BLE001
        pass
    print(json.dumps({"query": q, "items": items}, ensure_ascii=False))


if __name__ == "__main__":
    main()
