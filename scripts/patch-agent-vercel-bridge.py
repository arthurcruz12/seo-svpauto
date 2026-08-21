from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

replacements = {
    "`${API_BASE_URL}/api/v1/agents/route`": '"/api/agents?op=route"',
    "`${API_BASE_URL}/api/v1/agents/integrations`": '"/api/agents?op=integrations"',
    "`${API_BASE_URL}/api/v1/agents/status`": '"/api/agents?op=status"',
}

for old, new in replacements.items():
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Vercel agent bridge patch expected 1 match for {old}, got {count}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print("Agent controls routed through /api/agents while core SEO API remains unchanged")
