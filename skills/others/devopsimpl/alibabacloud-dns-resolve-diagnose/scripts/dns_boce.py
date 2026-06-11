"""
dns_boce.py - Playwright boce.aliyun.com probe wrapper.

Automates Alibaba Cloud probe platform via headless browser for nationwide DNS/HTTP probing.
boce.aliyun.com basic probing works without login.

API flow:
1. POST /data/api.json?action=BatchCreateOnceSiteMonitor  -> Create probe task
2. POST /data/api.json?action=DescribeSiteMonitorLog      -> Poll probe results (multiple times)
3. POST /api/detect/save_share.json                       -> Save share link
"""

import json
import re
import sys
import time
from typing import Optional


def _check_playwright():
    """Check if Playwright is available."""
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except ImportError:
        return False


class BoceProbeTool:
    """
    Alibaba Cloud probe platform (boce.aliyun.com) automation tool.

    Uses Playwright to control Chromium browser for DNS/HTTP probing,
    intercepts XHR responses or parses DOM for structured result data.
    """

    BASE_URL = "https://boce.aliyun.com"
    DNS_URL = f"{BASE_URL}/detect/dns"
    HTTP_URL = f"{BASE_URL}/detect/http"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None

    def launch(self):
        """Launch browser."""
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

    def close(self):
        """Close browser and Playwright."""
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def __enter__(self):
        self.launch()
        return self

    def __exit__(self, *args):
        self.close()

    def _fill_and_detect(self, page, url: str, value: str):
        """Fill domain/URL in probe page and click detect button."""
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(2)

        domain_input = page.locator("input[placeholder*='域名'], input[placeholder*='网站']").first
        if not domain_input.is_visible(timeout=3000):
            domain_input = page.locator(".detect-input input, .search-input input").first

        domain_input.click()
        domain_input.fill(value)
        time.sleep(0.5)

        detect_btn = page.locator("button:has-text('立即检测')").first
        if detect_btn.is_visible(timeout=3000):
            detect_btn.click()
        else:
            detect_btn = page.locator(
                "button:has-text('检测'), button:has-text('开始'), button:has-text('Detect')"
            ).first
            if detect_btn.is_visible(timeout=3000):
                detect_btn.click()
            else:
                domain_input.press("Enter")

    def dns_probe(self, domain: str, rtype: str = "A",
                  timeout: int = 90000) -> dict:
        """
        Execute DNS probe.

        Args:
            domain: Target domain
            rtype: Record type (A, AAAA, CNAME, MX, NS, TXT)
            timeout: Timeout in milliseconds

        Returns:
            dict: {
                "success": bool,
                "domain": str,
                "ip_count_map": {ip: count},
                "ip_rate_map": {ip: rate_str},
                "share_url": str,
                "total_nodes": int,
                "details": [{}],
                "error": str or None,
            }
        """
        page = self._context.new_page()
        monitor_logs = []

        def _capture_response(response):
            """Intercept DescribeSiteMonitorLog responses."""
            url = response.url
            try:
                if response.status == 200 and "/data/api.json" in url:
                    if "DescribeSiteMonitorLog" in url:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct:
                            data = response.json()
                            if isinstance(data, dict):
                                monitor_logs.append(data)
            except Exception:
                pass

        page.on("response", _capture_response)

        try:
            self._fill_and_detect(page, self.DNS_URL, domain)

            start_time = time.time()
            max_wait = timeout / 1000
            last_log_count = 0
            stable_rounds = 0

            while time.time() - start_time < max_wait:
                time.sleep(3)
                current_count = len(monitor_logs)
                if current_count > 0 and current_count == last_log_count:
                    stable_rounds += 1
                    if stable_rounds >= 3:
                        break
                else:
                    stable_rounds = 0
                last_log_count = current_count

            result = self._extract_dns_from_dom(page, domain)
            if result["success"]:
                return result

            if monitor_logs:
                return self._parse_monitor_logs_dns(monitor_logs, domain, page.url)

            return {
                "success": False,
                "domain": domain,
                "ip_count_map": {},
                "ip_rate_map": {},
                "share_url": page.url,
                "total_nodes": 0,
                "details": [],
                "error": "Cannot retrieve probe results, please visit probe link manually",
            }

        except Exception as e:
            return {
                "success": False,
                "domain": domain,
                "error": str(e),
                "ip_count_map": {},
                "ip_rate_map": {},
                "share_url": "",
                "total_nodes": 0,
                "details": [],
            }
        finally:
            page.close()

    def http_probe(self, url: str, timeout: int = 90000) -> dict:
        """
        Execute HTTP probe.

        Args:
            url: Target URL (e.g. https://www.example.com or domain)
            timeout: Timeout in milliseconds

        Returns:
            dict: {
                "success": bool,
                "url": str,
                "status_code_map": {code: count},
                "share_url": str,
                "total_nodes": int,
                "details": [{}],
                "error": str or None,
            }
        """
        if not url.startswith("http"):
            url = f"http://{url}"

        page = self._context.new_page()
        monitor_logs = []

        def _capture_response(response):
            resp_url = response.url
            try:
                if response.status == 200 and "/data/api.json" in resp_url:
                    if "DescribeSiteMonitorLog" in resp_url:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct:
                            data = response.json()
                            if isinstance(data, dict):
                                monitor_logs.append(data)
            except Exception:
                pass

        page.on("response", _capture_response)

        try:
            self._fill_and_detect(page, self.HTTP_URL, url)

            start_time = time.time()
            max_wait = timeout / 1000
            last_log_count = 0
            stable_rounds = 0

            while time.time() - start_time < max_wait:
                time.sleep(3)
                current_count = len(monitor_logs)
                if current_count > 0 and current_count == last_log_count:
                    stable_rounds += 1
                    if stable_rounds >= 3:
                        break
                else:
                    stable_rounds = 0
                last_log_count = current_count

            result = self._extract_http_from_dom(page, url)
            if result["success"]:
                return result

            if monitor_logs:
                return self._parse_monitor_logs_http(monitor_logs, url, page.url)

            return {
                "success": False,
                "url": url,
                "error": "Cannot retrieve probe results, please visit probe link manually",
                "status_code_map": {},
                "share_url": page.url,
                "total_nodes": 0,
                "details": [],
            }

        except Exception as e:
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "status_code_map": {},
                "share_url": "",
                "total_nodes": 0,
                "details": [],
            }
        finally:
            page.close()

    # --- DOM result extraction ---

    @staticmethod
    def _extract_dns_from_dom(page, domain: str) -> dict:
        """Extract DNS probe results from DOM result table."""
        try:
            data = page.evaluate("""
                () => {
                    let shareUrl = '';
                    const bodyText = document.body.innerText;
                    const shareMatch = bodyText.match(/https:\\/\\/boce\\.aliyun\\.com\\/detect\\/dns\\/[a-f0-9]+/);
                    if (shareMatch) shareUrl = shareMatch[0];

                    const ipCountMatch = bodyText.match(/解析结果IP(\\d+)个/);
                    const totalUniqueIPs = ipCountMatch ? parseInt(ipCountMatch[1]) : 0;

                    const tables = document.querySelectorAll('table');
                    if (tables.length < 2) return null;

                    const resultTable = tables[1];
                    const rows = resultTable.querySelectorAll('tr');
                    if (rows.length === 0) return null;

                    const ipCountMap = {};
                    const details = [];

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length < 5) return;

                        const location = cells[0].innerText.trim();
                        const sourceIP = cells[1].innerText.trim();
                        const dnsServer = cells[2].innerText.trim();
                        const resolveTime = cells[3].innerText.trim();
                        const resolveResult = cells[4].innerText.trim();

                        const ips = resolveResult.match(/\\d+\\.\\d+\\.\\d+\\.\\d+/g) || [];
                        ips.forEach(ip => {
                            ipCountMap[ip] = (ipCountMap[ip] || 0) + 1;
                        });

                        details.push({
                            location: location,
                            source_ip: sourceIP,
                            dns_server: dnsServer,
                            resolve_time: resolveTime,
                            resolve_result: resolveResult,
                            ips: ips,
                        });
                    });

                    return {
                        shareUrl: shareUrl,
                        totalUniqueIPs: totalUniqueIPs,
                        ipCountMap: ipCountMap,
                        details: details,
                        totalNodes: details.length,
                    };
                }
            """)

            if not data or data.get("totalNodes", 0) == 0:
                return {"success": False}

            total = data["totalNodes"]
            ip_rate_map = {}
            for ip, count in data["ipCountMap"].items():
                ip_rate_map[ip] = f"{count / total * 100:.1f}%"

            return {
                "success": True,
                "domain": domain,
                "ip_count_map": data["ipCountMap"],
                "ip_rate_map": ip_rate_map,
                "share_url": data.get("shareUrl", ""),
                "total_nodes": total,
                "details": data["details"],
                "error": None,
            }
        except Exception:
            return {"success": False}

    @staticmethod
    def _extract_http_from_dom(page, url: str) -> dict:
        """Extract HTTP probe results from DOM result table."""
        try:
            data = page.evaluate("""
                () => {
                    let shareUrl = '';
                    const bodyText = document.body.innerText;
                    const shareMatch = bodyText.match(/https:\\/\\/boce\\.aliyun\\.com\\/detect\\/http\\/[a-f0-9]+/);
                    if (shareMatch) shareUrl = shareMatch[0];

                    const tables = document.querySelectorAll('table');
                    if (tables.length < 2) return null;

                    const resultTable = tables[1];
                    const rows = resultTable.querySelectorAll('tr');
                    if (rows.length === 0) return null;

                    const statusCodeMap = {};
                    const details = [];

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length < 5) return;

                        const location = cells[0].innerText.trim();
                        const resolveIP = cells[1].innerText.trim();
                        const statusCodeRaw = cells[2] ? cells[2].innerText.trim() : '';
                        const totalTime = cells[3] ? cells[3].innerText.trim() : '';

                        const codeMatch = statusCodeRaw.match(/\\d+/);
                        const code = codeMatch ? codeMatch[0] : statusCodeRaw;
                        if (code) {
                            statusCodeMap[code] = (statusCodeMap[code] || 0) + 1;
                        }

                        details.push({
                            location: location,
                            resolve_ip: resolveIP,
                            status_code: code,
                            total_time: totalTime,
                        });
                    });

                    return {
                        shareUrl: shareUrl,
                        statusCodeMap: statusCodeMap,
                        details: details,
                        totalNodes: details.length,
                    };
                }
            """)

            if not data or data.get("totalNodes", 0) == 0:
                return {"success": False}

            return {
                "success": True,
                "url": url,
                "status_code_map": data["statusCodeMap"],
                "share_url": data.get("shareUrl", ""),
                "total_nodes": data["totalNodes"],
                "details": data["details"],
                "error": None,
            }
        except Exception:
            return {"success": False}

    # --- XHR result aggregation (fallback) ---

    @staticmethod
    def _parse_monitor_logs_dns(logs: list, domain: str, page_url: str) -> dict:
        """Aggregate DNS results from multiple DescribeSiteMonitorLog responses."""
        ip_count_map = {}
        details = []
        seen_keys = set()

        for log_resp in logs:
            items = log_resp.get("data", log_resp.get("Data", []))
            if isinstance(items, dict):
                items = items.get("items", items.get("Items", []))
            if not isinstance(items, list):
                continue

            for item in items:
                key = f"{item.get('city', '')}-{item.get('isp', '')}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                resolve_result = item.get("dnsResult", item.get("DnsResult", ""))
                ips = re.findall(r"\d+\.\d+\.\d+\.\d+", str(resolve_result))
                for ip in ips:
                    ip_count_map[ip] = ip_count_map.get(ip, 0) + 1

                details.append({
                    "location": f"{item.get('city', '')} {item.get('isp', '')}",
                    "source_ip": item.get("sourceIp", item.get("SourceIp", "")),
                    "resolve_result": resolve_result,
                    "ips": ips,
                })

        total = len(details)
        ip_rate_map = {}
        for ip, count in ip_count_map.items():
            ip_rate_map[ip] = f"{count / total * 100:.1f}%" if total > 0 else "0%"

        return {
            "success": total > 0,
            "domain": domain,
            "ip_count_map": ip_count_map,
            "ip_rate_map": ip_rate_map,
            "share_url": page_url,
            "total_nodes": total,
            "details": details,
            "error": None if total > 0 else "XHR data is empty",
        }

    @staticmethod
    def _parse_monitor_logs_http(logs: list, url: str, page_url: str) -> dict:
        """Aggregate HTTP results from multiple DescribeSiteMonitorLog responses."""
        status_code_map = {}
        details = []
        seen_keys = set()

        for log_resp in logs:
            items = log_resp.get("data", log_resp.get("Data", []))
            if isinstance(items, dict):
                items = items.get("items", items.get("Items", []))
            if not isinstance(items, list):
                continue

            for item in items:
                key = f"{item.get('city', '')}-{item.get('isp', '')}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                status = str(item.get("statusCode", item.get("StatusCode", "")))
                if status:
                    status_code_map[status] = status_code_map.get(status, 0) + 1

                details.append({
                    "location": f"{item.get('city', '')} {item.get('isp', '')}",
                    "source_ip": item.get("sourceIp", item.get("SourceIp", "")),
                    "status_code": status,
                })

        total = len(details)
        return {
            "success": total > 0,
            "url": url,
            "status_code_map": status_code_map,
            "share_url": page_url,
            "total_nodes": total,
            "details": details,
            "error": None if total > 0 else "XHR data is empty",
        }


# --- CLI entry point ---

def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Alibaba Cloud probe platform (boce.aliyun.com) tool")
    sub = parser.add_subparsers(dest="action")

    p = sub.add_parser("dns", help="Execute DNS probe")
    p.add_argument("--domain", required=True, help="Target domain")
    p.add_argument("--type", default="A", help="Record type (default A)")
    p.add_argument("--timeout", type=int, default=90, help="Timeout seconds (default 90)")

    p = sub.add_parser("http", help="Execute HTTP probe")
    p.add_argument("--url", required=True, help="Target URL")
    p.add_argument("--timeout", type=int, default=90, help="Timeout seconds (default 90)")

    p = sub.add_parser("both", help="Execute DNS + HTTP probe in parallel (subprocess)")
    p.add_argument("--domain", required=True, help="Target domain")
    p.add_argument("--timeout", type=int, default=90, help="Timeout seconds (default 90)")

    parser.add_argument("--visible", action="store_true", help="Show browser window (debug)")

    args = parser.parse_args()

    if not _check_playwright():
        print(json.dumps({
            "error": "Playwright not installed. Run: pip install playwright && playwright install chromium"
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    headless = not getattr(args, "visible", False)

    if args.action == "dns":
        with BoceProbeTool(headless=headless) as tool:
            result = tool.dns_probe(args.domain, args.type, args.timeout * 1000)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "http":
        with BoceProbeTool(headless=headless) as tool:
            result = tool.http_probe(args.url, args.timeout * 1000)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.action == "both":
        import subprocess as _sp

        script_path = os.path.abspath(__file__)
        visible_flag = ["--visible"] if not headless else []

        dns_cmd = [sys.executable, script_path, "dns",
                   "--domain", args.domain,
                   "--timeout", str(args.timeout)] + visible_flag
        http_cmd = [sys.executable, script_path, "http",
                    "--url", f"http://{args.domain}",
                    "--timeout", str(args.timeout)] + visible_flag

        dns_proc = _sp.Popen(dns_cmd, stdout=_sp.PIPE, stderr=_sp.PIPE, text=True)
        http_proc = _sp.Popen(http_cmd, stdout=_sp.PIPE, stderr=_sp.PIPE, text=True)

        dns_stdout, dns_stderr = dns_proc.communicate(timeout=args.timeout + 30)
        http_stdout, http_stderr = http_proc.communicate(timeout=args.timeout + 30)

        try:
            dns_result = json.loads(dns_stdout) if dns_stdout.strip() else {"error": dns_stderr or "no output"}
        except json.JSONDecodeError:
            dns_result = {"error": f"invalid json: {dns_stdout[:200]}"}

        try:
            http_result = json.loads(http_stdout) if http_stdout.strip() else {"error": http_stderr or "no output"}
        except json.JSONDecodeError:
            http_result = {"error": f"invalid json: {http_stdout[:200]}"}

        output = {
            "dns_probe": dns_result,
            "http_probe": http_result,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
