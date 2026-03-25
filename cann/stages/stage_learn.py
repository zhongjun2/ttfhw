import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class LearnStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._official_url: str | None = None
        self._rank: int | None = None
        self._nav_hops: int = 0
        self._accessible: int = 0
        self._broken: int = 0

    def setup(self) -> None:
        pass

    def run(self) -> None:
        search_cfg = self._config.get("search", {})
        keywords = search_cfg.get("keywords", "Ascend CANN")
        domains = search_cfg.get("official_domains", [])
        timeout = self._config.get("timeout", {}).get("learn_s", 60)

        self._mc.start("search")
        results = self._search(keywords, timeout)
        self._mc.stop("search")

        if not results:
            self._mc.add_error("search_no_results")
            self._mc.set_fail()
            return

        self._official_url, self._rank = self._find_official(results, domains)
        if not self._official_url:
            self._mc.add_error("no_official_link_found")
            self._mc.set_fail()
            return

        self._navigate_to_quickstart(timeout)
        self._check_links(timeout)

    def _search(self, keywords: str, timeout: int) -> list[str]:
        # NOTE: Bing Search API requires an API key in config.yaml:
        #   search.bing_api_key: "${BING_API_KEY}"
        # Without it, the call returns HTTP 401. Set env var BING_API_KEY before running.
        try:
            search_cfg = self._config.get("search", {})
            api_key = search_cfg.get("bing_api_key", "")
            r = requests.get(
                "https://api.bing.microsoft.com/v7.0/search",
                params={"q": keywords, "count": 10},
                headers={"Ocp-Apim-Subscription-Key": api_key},
                timeout=timeout,
            )
            r.raise_for_status()
            pages = r.json().get("webPages", {}).get("value", [])
            return [p["url"] for p in pages]
        except Exception as e:
            self._mc.add_error(f"search_error: {e}")
            return []

    def _find_official(self, urls: list[str], domains: list[str]):
        for i, url in enumerate(urls, start=1):
            if any(d in url for d in domains):
                return url, i
        return None, None

    def _navigate_to_quickstart(self, timeout: int) -> None:
        url = self._official_url
        hops = 0
        max_hops = 5
        with requests.Session() as session:
            while hops < max_hops:
                try:
                    resp = session.get(url, timeout=timeout)
                    hops += 1
                    if "快速入门" in resp.text or "quickstart" in resp.text.lower():
                        self._nav_hops = hops
                        return
                    soup = BeautifulSoup(resp.text, "html.parser")
                    link = soup.find("a", string=lambda t: t and "快速入门" in t)
                    if link:
                        url = urljoin(url, link["href"])
                    else:
                        break
                except Exception:
                    break
        self._nav_hops = hops
        if hops >= max_hops:
            self._mc.add_error("quickstart_not_reachable")
            self._mc.set_fail()

    def _check_links(self, timeout: int) -> None:
        try:
            with requests.Session() as session:
                resp = session.get(self._official_url, timeout=timeout)
                soup = BeautifulSoup(resp.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http"):
                        try:
                            r = session.head(href, timeout=5, allow_redirects=True)
                            if r.status_code < 400:
                                self._accessible += 1
                            else:
                                self._broken += 1
                                self._mc.set_warn()
                        except Exception:
                            self._broken += 1
                            self._mc.set_warn()
        except Exception as e:
            self._mc.add_error(f"link_check_error: {e}")

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "official_link_rank": self._rank,
            "nav_hops": self._nav_hops,
            "accessible_links": self._accessible,
            "broken_links": self._broken,
        })
        return d
