import pytest
from transparencyx.parse.sections import detect_sections

def test_detect_sections_standard():
    text = """
    Financial Disclosure Report
    
    ASSETS
    Some asset 1
    Some asset 2
    
    INCOME
    Some income source
    
    LIABILITIES
    Mortgage
    """
    
    sections = detect_sections(text)
    
    assert len(sections) == 3
    assert sections[0].name == "ASSETS"
    assert "Some asset 1" in sections[0].raw_text
    
    assert sections[1].name == "INCOME"
    assert "Some income source" in sections[1].raw_text
    
    assert sections[2].name == "LIABILITIES"
    assert "Mortgage" in sections[2].raw_text

def test_detect_sections_unclassified():
    text = "Just a bunch of random text with no known headers."
    
    sections = detect_sections(text)
    
    assert len(sections) == 1
    assert sections[0].name == "UNCLASSIFIED"
    assert sections[0].raw_text == text

def test_detect_sections_out_of_order():
    text = """
    POSITIONS
    Board member
    
    ASSETS
    Stock
    
    AGREEMENTS
    None
    """
    
    sections = detect_sections(text)
    
    assert len(sections) == 3
    
    # detect_sections sorts by appearance in text, so we check they are in the order they appear in the string
    assert sections[0].name == "POSITIONS"
    assert "Board member" in sections[0].raw_text
    
    assert sections[1].name == "ASSETS"
    assert "Stock" in sections[1].raw_text
    
    assert sections[2].name == "AGREEMENTS"
    assert "None" in sections[2].raw_text

def test_detect_sections_empty():
    sections = detect_sections("")
    assert len(sections) == 0

def test_detect_sections_boundaries():
    text = "ASSETS data INCOME more data"
    sections = detect_sections(text)
    
    assert len(sections) == 2
    
    # "ASSETS" starts at 0, "INCOME" starts at 12
    assert sections[0].name == "ASSETS"
    assert sections[0].start_index == 0
    assert sections[0].end_index == 12
    assert sections[0].raw_text == "ASSETS data"
    
    assert sections[1].name == "INCOME"
    assert sections[1].start_index == 12
    assert sections[1].end_index == 28
    assert sections[1].raw_text == "INCOME more data"

def test_detect_sections_corrupted_schedule_a_column_header():
    text = (
        'Filing Date: 05/15/2024\n'
        'S A: A  "U" I\n'
        'Asset Owner Value of Asset Income Type(s) Income Tx. >\n'
        '$1,000?\n'
        'Example Holding SP $1,001 - $15,000\n'
        'Exemption: Have you excluded from this report any other assets, '
        '"unearned" income, transactions, or liabilities?\n'
        'LIABILITIES\n'
        'None\n'
    )

    sections = detect_sections(text)

    assert sections[0].name == "ASSETS"
    assert sections[0].raw_text.startswith("Asset Owner Value of Asset Income Type(s)")
    assert "Example Holding" in sections[0].raw_text

def test_detect_sections_assets_starts_at_column_header():
    text = (
        'S A: A  "U" I\n'
        'Asset Owner Value of Asset Income Type(s) Income Tx. >\n'
        'Example Holding SP $1,001 - $15,000\n'
        'LIABILITIES\n'
    )

    sections = detect_sections(text)
    expected_start = text.find("Asset Owner Value of Asset Income Type(s)")

    assert sections[0].name == "ASSETS"
    assert sections[0].start_index == expected_start

def test_detect_sections_later_exemption_assets_not_assets_section():
    text = (
        'S A: A  "U" I\n'
        'Asset Owner Value of Asset Income Type(s) Income Tx. >\n'
        'Example Holding SP $1,001 - $15,000\n'
        'Exemption: Have you excluded from this report any other assets, '
        '"unearned" income, transactions, or liabilities?\n'
        'LIABILITIES\n'
        'None\n'
    )

    sections = detect_sections(text)
    expected_start = text.find("Asset Owner Value of Asset Income Type(s)")

    assets_sections = [section for section in sections if section.name == "ASSETS"]
    assert len(assets_sections) == 1
    assert assets_sections[0].start_index == expected_start
