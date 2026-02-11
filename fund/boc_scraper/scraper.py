from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


DEFAULT_BASE_URL = "https://www.bankofchina.com/sourcedb/srfd6_2024/index.html"


@dataclass
class ScrapeStats:
    total_pages: int
    total_rows: int
    start_page: int
    end_page: int
    elapsed_seconds: float


def _safe_decimal(s: str) -> Optional[Decimal]:
    s = (s or "").strip()
    if s in {"", "-", "—", "——", "N/A", "null", "NULL"}:
        return None
    # 统一去掉可能出现的千分位或百分号（若页面出现）
    s = s.replace(",", "").replace("%", "")
    try:
        return Decimal(s)
    except Exception:
        return None


def _safe_date(s: str) -> Optional[date]:
    s = (s or "").strip()
    # 期望格式：YYYY.MM.DD
    for fmt in ("%Y.%m.%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            continue
    # 回退：正则抓取任意分隔符的年月日
    m = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", s)
    if m:
        try:
            y, mth, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return date(y, mth, d)
        except Exception:
            return None
    return None


class BocScraper:
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 3,
        timeout_seconds: int = 20,
        request_delay_seconds: float = 0.4,
        fallback_discover_max_scan: int = 60,
        user_agent: Optional[str] = None,
    ):
        self.base_url = base_url
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds
        self.request_delay_seconds = request_delay_seconds
        self.fallback_discover_max_scan = fallback_discover_max_scan
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent
                or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Connection": "keep-alive",
            }
        )

    def _fetch(self, url: str, referer: Optional[str] = None) -> Optional[str]:
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                headers = {}
                if referer:
                    headers["Referer"] = referer
                else:
                    headers["Referer"] = self.base_url
                resp = self.session.get(url, timeout=self.timeout_seconds, headers=headers)
                # 修正编码：若服务端返回 ISO-8859-1 或缺失编码，则以 apparent_encoding 或 UTF-8 解码
                if not resp.encoding or resp.encoding.lower() in {"iso-8859-1", "latin-1", "ascii"}:
                    resp.encoding = resp.apparent_encoding or "utf-8"
                text = resp.text
                if resp.status_code == 200 and text:
                    return text
            except Exception as e:
                last_exc = e
            time.sleep(min(self.request_delay_seconds * attempt, 2.0))
        return None

    @staticmethod
    def _build_page_url(base_url: str, page_number: int) -> str:
        """
        BOC 站点分页常见模式：
        - 第 1 页：index.html
        - 第 N 页 (N>=2)：index_N.html
        """
        if page_number <= 1:
            return base_url
        return re.sub(r"index(?:_\d+)?\.html?$", f"index_{page_number}.html", base_url)

    @staticmethod
    def _discover_total_pages_from_html(html: str) -> Optional[int]:
        # 常见“共151页”字样
        m = re.search(r"共\s*(\d+)\s*页", html, flags=re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
        # 如果直接在 HTML 中未找到，尝试解析纯文本（处理 &nbsp;、全角空格等情况）
        try:
            soup = BeautifulSoup(html, "html.parser")
            page_text = soup.get_text(separator=" ", strip=True)
            page_text = page_text.replace("\xa0", " ").replace("\u3000", " ")
            m_text = re.search(r"共\s*(\d+)\s*页", page_text)
            if m_text:
                return int(m_text.group(1))
        except Exception:
            return None
        return None

    @staticmethod
    def _discover_total_pages_from_links(html: str) -> Optional[int]:
        """
        通过首页分页链接（如 index_2.html、index_151.html）推断总页数。
        """
        try:
            soup = BeautifulSoup(html, "html.parser")
            max_page = 1
            for a in soup.find_all("a", href=True):
                href = a["href"]
                m = re.search(r"index_(\d+)\.html?$", href, flags=re.IGNORECASE)
                if m:
                    try:
                        num = int(m.group(1))
                        if num > max_page:
                            max_page = num
                    except Exception:
                        continue
            return max_page if max_page >= 1 else None
        except Exception:
            return None

    def discover_total_pages(self) -> int:
        html = self._fetch(self.base_url, referer=self.base_url)
        if not html:
            return 1
        total = self._discover_total_pages_from_html(html)
        if total and total > 0:
            return total
        # 备选：从首页分页链接推断
        total = self._discover_total_pages_from_links(html)
        if total and total > 0:
            return total
        # 最后回退：有限次线性探测，避免长时间阻塞
        upper_bound = 1
        scan_limit = max(2, int(self.fallback_discover_max_scan))
        for pn in range(2, scan_limit + 1):
            page_url = self._build_page_url(self.base_url, pn)
            page_html = self._fetch(page_url, referer=self.base_url)
            if not page_html:
                upper_bound = pn - 1
                break
            upper_bound = pn
            # 轻微等待，避免请求过快
            time.sleep(min(self.request_delay_seconds, 0.3))
        return max(1, upper_bound)

    @staticmethod
    def _find_data_table(soup: BeautifulSoup):
        # 通过扫描每个 table 的各行，寻找包含关键列名的表头行
        required_keywords = {"产品代码", "产品名称", "单位净值", "累计净值", "截止日期"}
        for tbl in soup.find_all("table"):
            for tr in tbl.find_all("tr"):
                cells = tr.find_all(["th", "td"])
                if not cells:
                    continue
                texts = [c.get_text(separator=" ", strip=True) for c in cells]
                header_hits = sum(1 for t in texts if t in required_keywords)
                if header_hits >= 3:
                    return tbl
        return None

    @staticmethod
    def _iter_table_rows(table) -> Iterable[List[str]]:
        # yield 纯文本行
        for tr in table.find_all("tr"):
            tds = tr.find_all(["td"])
            if not tds:
                continue
            row = [td.get_text(separator=" ", strip=True) for td in tds]
            # 过滤掉很短或明显不是数据的行
            if len(row) < 6:
                continue
            yield row

    @staticmethod
    def _looks_like_header(row: List[str]) -> bool:
        header_keys = {"产品代码", "产品名称", "单位净值", "累计净值", "截止日期"}
        return any(cell in header_keys for cell in row)

    @staticmethod
    def _parse_row(row: List[str], page_url: str) -> Optional[dict]:
        """
        预期列（根据示例）：
        [产品代码, 产品名称, 单位净值, 累计净值, 每万份基金单位收益, 七日年收益率、净值增长率, 日净值增长率, 截止日期]
        """
        # 保守处理：只在列数 >= 8 时解析
        if len(row) < 8:
            return None
        product_code = row[0].strip()
        product_name = row[1].strip()

        unit_nav = _safe_decimal(row[2])
        cumulative_nav = _safe_decimal(row[3])
        income_per_10k = _safe_decimal(row[4])
        annualized_7d_or_growth = _safe_decimal(row[5])
        daily_growth_rate = _safe_decimal(row[6])
        as_of_date = _safe_date(row[7])

        # 基本校验
        if not product_code or not as_of_date:
            return None

        return {
            "product_code": product_code,
            "product_name": product_name,
            "unit_nav": unit_nav,
            "cumulative_nav": cumulative_nav,
            "income_per_10k": income_per_10k,
            "annualized_7d_or_growth": annualized_7d_or_growth,
            "daily_growth_rate": daily_growth_rate,
            "as_of_date": as_of_date,
            "source_page_url": page_url,
        }

    def _parse_records_internal(self, html: str, page_url: str) -> List[dict]:
        soup = BeautifulSoup(html, "html.parser")
        table = self._find_data_table(soup)
        records: List[dict] = []
        if table:
            for row in self._iter_table_rows(table):
                if self._looks_like_header(row):
                    continue
                rec = self._parse_row(row, page_url)
                if rec:
                    records.append(rec)
        return records

    def parse_records(self, html: str, page_url: str) -> List[dict]:
        # 直接解析
        records = self._parse_records_internal(html, page_url)
        if records:
            return records
        # 若未解析到，尝试跟进 iframe/frame src
        try:
            soup = BeautifulSoup(html, "html.parser")
            frames = soup.find_all(["iframe", "frame"])
            for fr in frames:
                src = (fr.get("src") or "").strip()
                if not src:
                    continue
                child_url = urljoin(page_url, src)
                child_html = self._fetch(child_url, referer=page_url)
                if not child_html:
                    continue
                child_records = self._parse_records_internal(child_html, child_url)
                if child_records:
                    return child_records
        except Exception:
            pass
        return []

    def scrape_range(self, start_page: int, end_page: int) -> Tuple[List[dict], ScrapeStats]:
        assert start_page >= 1 and end_page >= start_page
        all_records: List[dict] = []
        t0 = time.time()
        for pn in range(start_page, end_page + 1):
            page_url = self._build_page_url(self.base_url, pn)
            html = self._fetch(page_url, referer=self.base_url)
            if not html:
                # 若某页不可达，则跳过
                time.sleep(self.request_delay_seconds)
                continue
            page_records = self.parse_records(html, page_url)
            all_records.extend(page_records)
            time.sleep(self.request_delay_seconds)
        elapsed = time.time() - t0
        stats = ScrapeStats(
            total_pages=end_page - start_page + 1,
            total_rows=len(all_records),
            start_page=start_page,
            end_page=end_page,
            elapsed_seconds=elapsed,
        )
        return all_records, stats


