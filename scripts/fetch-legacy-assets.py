from pathlib import Path
import urllib.request

LEGACY_BASE = "https://seo-svpauto-bsjdt0ajh-arthurcruz12s-projects.vercel.app"
ASSETS = [
    ("/assets/index-DifEdwF3.js", "application/javascript"),
    ("/assets/react-SLA1hOw8.js", "application/javascript"),
    ("/assets/icons-CNAm9td9.js", "application/javascript"),
    ("/assets/index-C6S3n_g7.css", "text/css"),
]

out_dir = Path("dist/assets")
out_dir.mkdir(parents=True, exist_ok=True)

for asset_path, expected_type in ASSETS:
    request = urllib.request.Request(
        f"{LEGACY_BASE}{asset_path}",
        headers={"User-Agent": "seo-frontend-recovery/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
        content_type = response.headers.get("Content-Type", "")

    if expected_type not in content_type:
        raise RuntimeError(
            f"Unexpected content type for {asset_path}: {content_type}"
        )
    if len(body) < 100:
        raise RuntimeError(f"Asset too small: {asset_path} ({len(body)} bytes)")

    destination = out_dir / Path(asset_path).name
    destination.write_bytes(body)
    print(f"restored {destination} ({len(body)} bytes, {content_type})")
