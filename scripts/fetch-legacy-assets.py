from http.cookiejar import CookieJar
from pathlib import Path
from urllib.request import HTTPCookieProcessor, Request, build_opener

HOST = "https://seo-svpauto-bsjdt0ajh-arthurcruz12s-projects.vercel.app"
SHARE_URL = "https://seo-svpauto-bsjdt0ajh-arthurcruz12s-projects.vercel.app/?_vercel_share=eAoTaVsaR2BXLwcd1GA3LJjslSZW6y4t"
ASSETS = [
    "/assets/index-DifEdwF3.js",
    "/assets/react-SLA1hOw8.js",
    "/assets/icons-CNAm9td9.js",
    "/assets/index-C6S3n_g7.css",
    "/assets/charts-B-xu7Qo0.js",
]

jar = CookieJar()
opener = build_opener(HTTPCookieProcessor(jar))
headers = {"User-Agent": "Mozilla/5.0 seo-static-recovery/1.0"}

with opener.open(Request(SHARE_URL, headers=headers), timeout=30) as response:
    share_body = response.read()
    print("share final url:", response.geturl())
    print("share content type:", response.headers.get("Content-Type", ""))
    print("share bytes:", len(share_body))
print("cookies:", [(c.domain, c.name, c.value[:12] + "...") for c in jar])

out = Path("dist/assets")
out.mkdir(parents=True, exist_ok=True)

for asset_path in ASSETS:
    with opener.open(Request(HOST + asset_path, headers=headers), timeout=30) as response:
        data = response.read()
        content_type = response.headers.get("Content-Type", "")
        final_url = response.geturl()
    print(f"asset {asset_path}: {len(data)} bytes ({content_type}); final={final_url}")
    print("asset prefix:", data[:80])

    if asset_path.endswith(".js") and "javascript" not in content_type:
        raise RuntimeError(f"Unexpected content type for {asset_path}: {content_type}")
    if asset_path.endswith(".css") and "css" not in content_type:
        raise RuntimeError(f"Unexpected content type for {asset_path}: {content_type}")

    target = out / asset_path.rsplit("/", 1)[-1]
    target.write_bytes(data)
    print(f"Recovered {asset_path}: {len(data)} bytes ({content_type})")
