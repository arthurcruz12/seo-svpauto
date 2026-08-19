from pathlib import Path

names = {
    "index-DifEdwF3.js",
    "react-SLA1hOw8.js",
    "icons-CNAm9td9.js",
    "index-C6S3n_g7.css",
    "charts-B-xu7Qo0.js",
}

print("--- exact legacy assets in build filesystem ---")
for path in Path("/vercel").rglob("*"):
    try:
        if path.is_file() and path.name in names:
            print(path, path.stat().st_size)
    except OSError:
        pass

print("--- likely cached JS/CSS files over 40KB ---")
count = 0
for path in Path("/vercel").rglob("*"):
    try:
        if path.is_file() and path.suffix in {".js", ".css"} and path.stat().st_size > 40_000:
            print(path, path.stat().st_size)
            count += 1
            if count >= 100:
                break
    except OSError:
        pass

raise SystemExit(1)
