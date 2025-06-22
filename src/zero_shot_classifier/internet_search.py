"""Performing internet searches using Google Custom Search API."""

import datetime
import re
from pathlib import Path
from time import sleep
from typing import Any

import chardet
import requests
import yaml
from bs4 import BeautifulSoup
from googleapiclient.discovery import build


class SearchClient:
    """Client for performing Google Custom Search API queries and saving results.

    This class handles searching for keywords using Google Custom Search,
    extracting snippets (including HTML snippets), and saving the results
    as YAML files. It supports pagination to fetch multiple pages of results.

    Attributes:
    ----------
    api_key : str
        Google API developer key.
    cse_id : str
        Custom Search Engine ID.
    output_dir : Path
        Directory to save YAML response files.
    max_results : int
        Maximum number of search results to retrieve.
    results_per_page : int
        Number of results per API call/page.
    headers : dict
        HTTP headers used in web requests (User-Agent).
    """

    def __init__(
        self,
        api_key: str,
        cse_id: str,
        output_dir: Path = Path("data/response_yaml"),
        max_results: int = 30,
        results_per_page: int = 10,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    ):
        """Initialize SearchClient instance.

        Parameters
        ----------
        api_key : str
            Google API developer key.
        cse_id : str
            Custom Search Engine ID.
        output_dir : Path, optional
            Directory path to save output YAML files (default is data/response_yaml).
        max_results : int, optional
            Maximum total results to fetch (default is 30).
        results_per_page : int, optional
            Number of results to fetch per API request/page (default is 10).
        user_agent : str, optional
            User-Agent header string for HTTP requests (default is Windows 10 Chrome).
        """
        self.api_key = api_key
        self.cse_id = cse_id
        self.output_dir = output_dir
        self.max_results = max_results
        self.results_per_page = results_per_page
        self.headers = {"User-Agent": user_agent}

        self._make_dir(self.output_dir)

    def _make_dir(self, path: Path) -> None:
        """Create directory if it does not exist.

        Parameters
        ----------
        path : Path
            Directory path to create.
        """
        path.mkdir(parents=True, exist_ok=True)

    def _clean_text(self, text: str, max_chars: int = 1500) -> str:
        """Clean text by normalizing whitespace and truncating.

        Parameters
        ----------
        text : str
            Input text to clean.
        max_chars : int, optional
            Maximum number of characters to keep (default is 1500).

        Returns:
        -------
        str
            Cleaned and truncated text.
        """
        text = re.sub(r"\n+", "\n", text)
        return text.strip()[:max_chars]

    def _fetch_full_text(self, url: str, max_chars: int = 1500) -> str:
        """Placeholder for full text fetching from URL.

        Full text extraction is currently disabled/not used.

        Parameters
        ----------
        url : str
            URL to fetch full text from.
        max_chars : int, optional
            Maximum number of characters to return (default is 1500).

        Returns:
        -------
        str
            Empty string (full text fetching disabled).
        """
        return ""

    def _fetch_html_snippet(self, url: str) -> str:
        """Fetch snippet text from a web page by parsing HTML content.

        Attempts to retrieve and extract meaningful snippet text from the
        given URL by downloading HTML and parsing paragraph and block elements.

        Parameters
        ----------
        url : str
            URL to fetch snippet from.

        Returns:
        -------
        str
            Extracted snippet text, cleaned and truncated.
            Returns empty string on failure or non-HTML content.
        """
        try:
            res = requests.get(url, timeout=15, headers=self.headers, verify=False)
            if "text/html" not in res.headers.get("Content-Type", ""):
                return ""

            encoding = chardet.detect(res.content)["encoding"] or "utf-8"
            soup = BeautifulSoup(
                res.content.decode(encoding, errors="replace"), "html.parser"
            )

            paragraphs = soup.find_all("p")
            if len(paragraphs) >= 3:
                text = "\n".join(p.get_text(strip=True) for p in paragraphs[:6])
            else:
                blocks = soup.find_all(["p", "div", "span"])
                text = "\n".join(
                    b.get_text(strip=True)
                    for b in blocks
                    if len(b.get_text(strip=True)) > 40
                )

            return self._clean_text(text)

        except Exception as e:
            print(f"⚠️ HTML snippet fetch failed for {url}: {e}")
            return ""

    def get_search_response(self, keyword: str) -> dict[str, Any] | None:
        """Perform Google Custom Search API query for a keyword and collect results.

        This method paginates through results until max_results are collected or
        no further pages exist.

        Parameters
        ----------
        keyword : str
            Search keyword or query string.

        Returns:
        -------
        dict or None
            Dictionary containing keyword, snapshot date/time, and list of results.
            Each result includes title, link, and snippet (HTML).
            Returns None if no results found.
        """
        today = datetime.datetime.today().strftime("%Y%m%d")
        timestamp = datetime.datetime.today().strftime("%Y/%m/%d %H:%M:%S")

        service = build("customsearch", "v1", developerKey=self.api_key)

        results: list[dict[str, str]] = []
        start_index = 1

        print(f"🔍 Searching: {keyword}")

        while len(results) < self.max_results:
            try:
                sleep(1)
                res = (
                    service.cse()
                    .list(
                        q=keyword,
                        cx=self.cse_id,
                        lr="lang_ja",
                        num=self.results_per_page,
                        start=start_index,
                    )
                    .execute()
                )

                items = res.get("items", [])
                for item in items:
                    results.append(
                        {
                            "title": item.get("title"),
                            "link": item.get("link"),
                            "snippet": item.get("htmlSnippet"),
                            # Use plain snippet text instead if desired:
                            # "snippet": item.get("snippet"),
                        }
                    )

                if "nextPage" not in res.get("queries", {}):
                    break
                start_index = res["queries"]["nextPage"][0]["startIndex"]

            except Exception as e:
                print(f"⚠️ Error during API call: {e}")
                break

        if not results:
            print("⚠️ No results found.")
            return None

        return {
            "keyword": keyword,
            "snapshot_date": today,
            "timestamp": timestamp,
            "results": results[: self.max_results],
        }

    def save_results(self, data: dict[str, Any]) -> None:
        """Save search results dictionary to a YAML file.

        Parameters
        ----------
        data : dict
            Search results dictionary returned by get_search_response.
        """
        if not data:
            print("⚠️ No data to save.")
            return

        safe_keyword = data["keyword"].replace("/", "_")
        today = data["snapshot_date"]
        filepath = self.output_dir / f"{safe_keyword}_{today}.yaml"

        with filepath.open("w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)

        print(f"✅ Saved: {filepath}")

    def search_and_save(self, keywords: list[str]) -> None:
        """Perform search and save results for multiple keywords.

        Parameters
        ----------
        keywords : list of str
            List of keyword strings to search and save results for.
        """
        for kw in keywords:
            data = self.get_search_response(kw)
            if data is not None:
                self.save_results(data)


if __name__ == "__main__":
    path_keys = Path(__file__).parents[2] / "keys.yaml"
    with path_keys.open("r", encoding="utf-8") as f:
        keys = yaml.safe_load(f)

    GOOGLE_API_KEY = keys["google"]["api_key"]
    CUSTOM_SEARCH_ENGINE_ID = keys["google"]["custom_search_engine_id"]

    client = SearchClient(GOOGLE_API_KEY, CUSTOM_SEARCH_ENGINE_ID)

    target_keywords = [
        "NWC5E-STP1-Y-YL-10",
        "D/MS3100A14S-9SW",
    ]

    client.search_and_save(target_keywords)
