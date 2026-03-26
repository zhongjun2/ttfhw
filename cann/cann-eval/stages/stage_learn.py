# stages/stage_learn.py
import time
import requests
from googlesearch import search
from stages.base import BaseStage
from metrics.collector import MetricsCollector


class LearnStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._mc = MetricsCollector()
        self._official_url: str | None = None
        self._official_rank: int | None = None
        self._official_accessible: bool = False
        self._quickstart_url: str | None = None
        self._quickstart_found: bool = False
        self._qwen2_guide_url: str | None = None
        self._qwen2_guide_found: bool = False
        self._accessible_links: int = 0
        self._broken_links: int = 0

    def setup(self) -> None:
        pass

    def run(self) -> None:
        timeout = self._config.get("timeout", {}).get("learn_s", 60)
        self._mc.start("search")
        try:
            self._run_search(timeout)
        finally:
            self._mc.stop("search")

    def _run_search(self, timeout: int) -> None:
        # Step 1: 搜索官方文档入口
        try:
            results = list(search("CANN 昇腾 安装", num_results=10, sleep_interval=2))
        except Exception as e:
            self._mc.add_error(
                phenomenon=f"Google 搜索失败: {e}",
                severity="P0",
                cause="网络问题或 Google 封禁",
                solution="检查网络连接，或稍后重试",
            )
            self._mc.set_fail()
            return

        for i, url in enumerate(results, start=1):
            if "hiascend.com" in url:
                self._official_url = url
                self._official_rank = i
                break

        if not self._official_url:
            self._mc.add_error(
                phenomenon="搜索结果中未找到 hiascend.com 官方链接",
                severity="P1",
                cause="官方文档 SEO 排名低，或搜索结果受地区影响",
                solution="直接访问 hiascend.com 文档页面",
            )
            self._mc.set_fail()

        # Step 2: 搜索 Quick Start 链接
        time.sleep(2)
        try:
            qs_results = list(search("CANN 快速入门 site:hiascend.com", num_results=5, sleep_interval=2))
            if qs_results:
                self._quickstart_url = qs_results[0]
                self._quickstart_found = True
        except Exception:
            pass
        if not self._quickstart_found:
            fallback = self._config.get("quickstart_url", "")
            if fallback:
                self._quickstart_url = fallback
                self._quickstart_found = True

        # Step 3: 搜索 Qwen2 部署文档
        time.sleep(2)
        try:
            qwen_results = list(search("Qwen2 CANN 昇腾 部署", num_results=5, sleep_interval=2))
            if qwen_results:
                self._qwen2_guide_url = qwen_results[0]
                self._qwen2_guide_found = True
        except Exception:
            pass

        # Step 4: 检查所有找到的链接可达性（同时更新 official_accessible）
        urls_to_check = [u for u in [
            self._official_url,
            self._quickstart_url,
            self._qwen2_guide_url,
        ] if u]
        self._check_links(urls_to_check, timeout)

    def _check_links(self, urls: list[str], timeout: int) -> None:
        for url in urls:
            try:
                r = requests.head(url, timeout=timeout, allow_redirects=True)
                if r.status_code < 400:
                    self._accessible_links += 1
                    if url == self._official_url:
                        self._official_accessible = True
                else:
                    self._broken_links += 1
                    self._mc.add_error(
                        phenomenon=f"链接不可访问: {url} (HTTP {r.status_code})",
                        severity="P2",
                        cause="文档 URL 变更或服务不可用",
                        solution="手动访问确认最新链接",
                    )
                    self._mc.set_warn()
            except Exception as e:
                self._broken_links += 1
                self._mc.add_error(
                    phenomenon=f"链接检查失败: {url}",
                    severity="P2",
                    cause=str(e),
                    solution="检查网络连接",
                )
                self._mc.set_warn()

    def verify(self) -> bool:
        return self._mc.status() != "fail"

    def teardown(self) -> None:
        pass

    def metrics(self) -> dict:
        d = self._mc.to_dict()
        d.update({
            "official_link_rank": self._official_rank,
            "official_url": self._official_url,
            "official_accessible": self._official_accessible,
            "quickstart_url": self._quickstart_url,
            "quickstart_found": self._quickstart_found,
            "qwen2_guide_url": self._qwen2_guide_url,
            "qwen2_guide_found": self._qwen2_guide_found,
            "accessible_links": self._accessible_links,
            "broken_links": self._broken_links,
        })
        return d
