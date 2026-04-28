"""
Tests for v0.15 real-data bug fix: SCHEDULE A section detection.

Validates that detect_sections() and extract_asset_candidates()
handle the real House disclosure header format:
    Schedule A: Assets and "Unearned" Income
"""
from transparencyx.parse.sections import detect_sections
from transparencyx.normalize.assets import extract_asset_candidates


# Synthetic text mimicking the real House disclosure structure:
# "Schedule A" header appears before actual asset data,
# and the word INCOME appears inside that header.
REAL_HOUSE_DISCLOSURE_TEXT = """Financial Disclosure Report
Clerk of the House of Representatives
Filer Information
Name: Hon. Test Member
Schedule A: Assets and "Unearned" Income
Asset Owner Value of Asset Income Type(s)
US Treasury Bonds [ST] SP $1,001 - $15,000 None
Tech Corp Stock (TECH) [ST] SP $50,001 - $100,000 Dividends $1,001 - $2,500
Municipal Bond Fund [MF] SP $15,001 - $50,000 None
LIABILITIES
SP City National Bank Loan $1,000,001 - $5,000,000
"""


class TestScheduleASectionDetection:
    def test_schedule_a_detected_as_section(self):
        """SCHEDULE A header in real House disclosures must produce a SCHEDULE A section."""
        sections = detect_sections(REAL_HOUSE_DISCLOSURE_TEXT)
        section_names = [s.name for s in sections]
        assert "SCHEDULE A" in section_names

    def test_assets_contains_asset_data(self):
        """The ASSETS section must contain the actual asset listing text."""
        sections = detect_sections(REAL_HOUSE_DISCLOSURE_TEXT)
        assets = [s for s in sections if s.name == "ASSETS"][0]
        assert assets.raw_text.startswith("Asset Owner Value of Asset Income Type(s)")
        assert "$1,001 - $15,000" in assets.raw_text
        assert "Tech Corp Stock" in assets.raw_text

    def test_asset_candidates_from_assets_column_header(self):
        """extract_asset_candidates must accept ASSETS sections from the column header."""
        sections = detect_sections(REAL_HOUSE_DISCLOSURE_TEXT)
        assets = [s for s in sections if s.name == "ASSETS"][0]
        candidates = extract_asset_candidates(assets)
        assert len(candidates) >= 2
        names = [c.cleaned_name for c in candidates]
        assert any("US Treasury Bonds" in n for n in names)
        assert any("Tech Corp Stock" in n for n in names)

    def test_liabilities_section_still_detected(self):
        """LIABILITIES section must still be detected after SCHEDULE A."""
        sections = detect_sections(REAL_HOUSE_DISCLOSURE_TEXT)
        section_names = [s.name for s in sections]
        assert "LIABILITIES" in section_names

    def test_existing_assets_keyword_still_works(self):
        """The plain ASSETS keyword must still work for demo/synthetic data."""
        text = """ASSETS
US Treasury Bonds [ST] $1,001 - $15,000
LIABILITIES
None"""
        sections = detect_sections(text)
        section_names = [s.name for s in sections]
        assert "ASSETS" in section_names
        assets_section = [s for s in sections if s.name == "ASSETS"][0]
        candidates = extract_asset_candidates(assets_section)
        assert len(candidates) >= 1
