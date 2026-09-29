import http.cookiejar
import re
import urllib.parse
import urllib.request

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# 1. GET login page to obtain CSRF cookie and token
resp = opener.open("http://127.0.0.1:8000/login/")
html = resp.read().decode("utf-8")
csrf_match = re.search(r'name=["\']csrfmiddlewaretoken["\']\s+value=["\']([^"\']+)["\']', html)
csrf_token = csrf_match.group(1) if csrf_match else ""
login_has_text = "authorized personnel only" in html.lower() or "master portal key" in html.lower()
print(
    f"[OK] Login page GET status: {resp.status}, CSRF token found: {'Yes' if csrf_token else 'No'}, Login UI Match: {login_has_text}"
)

# 2. POST login credentials
login_data = urllib.parse.urlencode(
    {"csrfmiddlewaretoken": csrf_token, "password": "forensiq2026", "next": "/"}
).encode("utf-8")

req = urllib.request.Request(
    "http://127.0.0.1:8000/login/",
    data=login_data,
    headers={"Referer": "http://127.0.0.1:8000/login/", "User-Agent": "ForensiQ-TestClient/1.0"},
)

login_resp = opener.open(req)
print(f"[OK] Login POST status: {login_resp.status}, Final URL: {login_resp.url}")

# 3. Test each application page
urls_to_test = [
    ("/", "Investigation Platform"),
    ("/bank/", "Q-Bank"),
    ("/mail/", "Q-Mail"),
    ("/chat/", "Q-Chat"),
    ("/verify/", "Q-Verify"),
    ("/scan/", "Q-Scan"),
    ("/demo/tabulator/", "Forensic Transaction Ledger"),
    ("/demo/sandbox/", "Analytics Visualizer"),
]

print("\n--- Testing All Page Routes ---")
all_passed = login_has_text
for path, expected_text in urls_to_test:
    url = f"http://127.0.0.1:8000{path}"
    try:
        page_resp = opener.open(url)
        content = page_resp.read().decode("utf-8")
        status = page_resp.status
        has_text = expected_text.lower() in content.lower()
        has_theme_css = "theme.css" in content
        has_tailwind = "tailwind-theme.js" in content

        status_str = f"Status: {status} | Matches: {has_text} | Theme CSS: {has_theme_css} | Tailwind Theme: {has_tailwind}"
        print(
            f"[{'PASS' if status == 200 and has_text else 'FAIL'}] {path.ljust(20)} -> {status_str}"
        )
        if status != 200 or not has_text:
            all_passed = False
    except Exception as e:
        print(f"[ERROR] {path.ljust(20)} -> {e}")
        all_passed = False

# 4. Test Static Theme Files
print("\n--- Testing Static Theme Files ---")
static_assets = [
    "/static/ui/css/theme.css",
    "/static/ui/js/tailwind-theme.js",
    "/static/ui/js/theme-manager.js",
    "/static/core/images/letter_q_orange.png",
]

for asset in static_assets:
    url = f"http://127.0.0.1:8000{asset}"
    try:
        asset_resp = opener.open(url)
        print(
            f"[PASS] {asset.ljust(45)} -> Status: {asset_resp.status}, Size: {len(asset_resp.read())} bytes"
        )
    except Exception as e:
        print(f"[FAIL] {asset.ljust(45)} -> {e}")
        all_passed = False

print("\n==========================================")
print(f"Overall Verification Result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
print("==========================================")
