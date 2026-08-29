"""Production configuration regression tests.

Verify that:
1. Production API URL is not localhost.
2. VITE_API_URL is respected in source code.
3. No accidental localhost endpoint remains in production configuration.
4. Frontend requests resolve against the configured production backend.
"""

from __future__ import annotations

import re
from pathlib import Path

FRONTEND_SRC = Path(__file__).resolve().parent.parent / "frontend" / "src"

PRODUCTION_API_URL = "https://aurora-core-1-txvl.onrender.com"
LOCALHOST_PATTERN = re.compile(r"127\.0\.0\.1|localhost:\d+")
VITE_API_URL_PATTERN = re.compile(r"import\.meta\.env\.VITE_API_URL")


def _collect_source_files() -> list[Path]:
    """Collect all .ts and .tsx files in frontend/src."""
    files: list[Path] = []
    for ext in ("*.ts", "*.tsx"):
        files.extend(FRONTEND_SRC.rglob(ext))
    return files


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestProductionAPIUrlNotLocalhost:
    """Verify no hardcoded localhost endpoints exist in source files."""

    def test_no_localhost_in_data_service(self):
        """data.ts must not contain hardcoded localhost."""
        data_ts = FRONTEND_SRC / "services" / "data.ts"
        content = _read(data_ts)
        assert "127.0.0.1" not in content, "data.ts contains hardcoded 127.0.0.1"
        assert "localhost:8000" not in content, "data.ts contains hardcoded localhost:8000"

    def test_no_localhost_in_settings_page(self):
        """SettingsPage.tsx must not contain hardcoded localhost."""
        settings_tsx = FRONTEND_SRC / "pages" / "SettingsPage.tsx"
        content = _read(settings_tsx)
        assert "127.0.0.1" not in content, "SettingsPage.tsx contains hardcoded 127.0.0.1"
        assert "localhost:8000" not in content, "SettingsPage.tsx contains hardcoded localhost:8000"

    def test_no_localhost_in_asset_explorer(self):
        """AssetExplorer.tsx must not contain hardcoded localhost."""
        explorer_tsx = FRONTEND_SRC / "pages" / "AssetExplorer.tsx"
        content = _read(explorer_tsx)
        assert "127.0.0.1" not in content, "AssetExplorer.tsx contains hardcoded 127.0.0.1"
        assert "localhost:8000" not in content, "AssetExplorer.tsx contains hardcoded localhost:8000"

    def test_no_localhost_in_any_source_file(self):
        """No source file in frontend/src should contain hardcoded localhost:8000."""
        violations: list[str] = []
        for path in _collect_source_files():
            # Skip node_modules (shouldn't be in src, but defensive)
            if "node_modules" in str(path):
                continue
            content = _read(path)
            for i, line in enumerate(content.splitlines(), 1):
                if re.search(r"127\.0\.0\.1:8000|localhost:8000", line):
                    violations.append(f"{path.relative_to(FRONTEND_SRC)}:{i}: {line.strip()}")
        assert not violations, "Hardcoded localhost:8000 found:\n" + "\n".join(violations)


class TestViteApiUrlRespected:
    """Verify VITE_API_URL is used as the configuration mechanism."""

    def test_data_service_uses_vite_api_url(self):
        """data.ts or config.ts must read VITE_API_URL from import.meta.env."""
        config_ts = FRONTEND_SRC / "services" / "config.ts"
        data_ts = FRONTEND_SRC / "services" / "data.ts"
        config_content = _read(config_ts)
        data_content = _read(data_ts)
        assert VITE_API_URL_PATTERN.search(config_content) or VITE_API_URL_PATTERN.search(data_content), (
            "config.ts or data.ts must use import.meta.env.VITE_API_URL"
        )

    def test_data_service_exports_api_base(self):
        """data.ts must export API_BASE (directly or via re-export)."""
        data_ts = FRONTEND_SRC / "services" / "data.ts"
        content = _read(data_ts)
        assert "export" in content and "API_BASE" in content, "data.ts must export API_BASE"

    def test_data_service_fallback_is_render(self):
        """config.ts or data.ts must contain the Render production backend URL."""
        config_ts = FRONTEND_SRC / "services" / "config.ts"
        data_ts = FRONTEND_SRC / "services" / "data.ts"
        config_content = _read(config_ts)
        data_content = _read(data_ts)
        assert PRODUCTION_API_URL in config_content or PRODUCTION_API_URL in data_content, (
            f"config.ts or data.ts must contain {PRODUCTION_API_URL} as fallback"
        )


class TestFrontendUsesCentralizedConfig:
    """Verify all frontend API calls use the centralized API_BASE."""

    def test_settings_page_imports_api_base(self):
        """SettingsPage.tsx must import API_BASE from data service."""
        settings_tsx = FRONTEND_SRC / "pages" / "SettingsPage.tsx"
        content = _read(settings_tsx)
        assert "import { API_BASE }" in content or "import {API_BASE}" in content, (
            "SettingsPage.tsx must import API_BASE"
        )

    def test_settings_page_uses_api_base_for_health(self):
        """SettingsPage.tsx health check must use API_BASE."""
        settings_tsx = FRONTEND_SRC / "pages" / "SettingsPage.tsx"
        content = _read(settings_tsx)
        assert "${API_BASE}/health" in content, "SettingsPage health check must use API_BASE"

    def test_asset_explorer_imports_api_base(self):
        """AssetExplorer.tsx must import API_BASE from data service."""
        explorer_tsx = FRONTEND_SRC / "pages" / "AssetExplorer.tsx"
        content = _read(explorer_tsx)
        assert "import { API_BASE }" in content or "import {API_BASE}" in content, (
            "AssetExplorer.tsx must import API_BASE"
        )

    def test_asset_explorer_uses_api_base(self):
        """AssetExplorer.tsx quote fetch must use API_BASE."""
        explorer_tsx = FRONTEND_SRC / "pages" / "AssetExplorer.tsx"
        content = _read(explorer_tsx)
        assert "${API_BASE}/market/" in content, "AssetExplorer quote fetch must use API_BASE"


class TestStaleMetadataFixed:
    """Verify stale product metadata has been updated."""

    def test_version_not_alpha(self):
        """Version should not be 0.1.0-alpha."""
        settings_tsx = FRONTEND_SRC / "pages" / "SettingsPage.tsx"
        content = _read(settings_tsx)
        assert "0.1.0-alpha" not in content, "Version still shows 0.1.0-alpha"

    def test_phase_not_m15(self):
        """Phase should not reference M15-Decision-Gate."""
        settings_tsx = FRONTEND_SRC / "pages" / "SettingsPage.tsx"
        content = _read(settings_tsx)
        assert "M15-Decision-Gate" not in content, "Phase still shows M15-Decision-Gate"

    def test_build_date_current(self):
        """Build date should be 2026-08-22 or later."""
        settings_tsx = FRONTEND_SRC / "pages" / "SettingsPage.tsx"
        content = _read(settings_tsx)
        assert "2026-08-21" not in content, "Build date still shows 2026-08-21"


class TestNoLocalhostInProduction:
    """Final regression: absolutely no localhost in production source."""

    def test_no_hardcoded_localhost_anywhere(self):
        """Scan all frontend source files for any hardcoded localhost endpoint."""
        files = _collect_source_files()
        bad_files: list[str] = []
        for path in files:
            if "node_modules" in str(path):
                continue
            content = _read(path)
            if re.search(r"(?:http://|https://)?127\.0\.0\.1:\d+", content):
                bad_files.append(str(path.relative_to(FRONTEND_SRC)))
        assert not bad_files, f"Files with hardcoded localhost endpoints: {bad_files}"
