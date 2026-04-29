from pathlib import Path

from transparencyx.profile.registry import build_member_record, build_registry


def test_build_member_record_single_file(monkeypatch):
    monkeypatch.setattr(
        "transparencyx.profile.registry._extract_text_from_pdf",
        lambda pdf_path: "Name: Hon. Nancy Pelosi\nStatus: Member\n",
    )

    record = build_member_record(Path("data/raw/house/2023/10059734.pdf"))

    assert record == {
        "member_name": "Nancy Pelosi",
        "politician_id": None,
        "filing_year": None,
        "source": "house",
        "disclosure_path": "data\\raw\\house\\2023\\10059734.pdf",
    }


def test_build_registry_multiple_files(monkeypatch):
    names_by_path = {
        "a.pdf": "Name: Hon. Alpha Member\n",
        "b.pdf": "Name: Hon. Beta Member\n",
    }
    monkeypatch.setattr(
        "transparencyx.profile.registry._extract_text_from_pdf",
        lambda pdf_path: names_by_path[pdf_path.name],
    )

    registry = build_registry([Path("b.pdf"), Path("a.pdf")])

    assert [record["member_name"] for record in registry] == [
        "Alpha Member",
        "Beta Member",
    ]


def test_build_member_record_unknown_name_fallback(monkeypatch):
    monkeypatch.setattr(
        "transparencyx.profile.registry._extract_text_from_pdf",
        lambda pdf_path: "Status: Member\n",
    )

    record = build_member_record(Path("unknown.pdf"))

    assert record["member_name"] == "Unknown"


def test_build_registry_deterministic_ordering(monkeypatch):
    monkeypatch.setattr(
        "transparencyx.profile.registry._extract_text_from_pdf",
        lambda pdf_path: f"Name: {pdf_path.stem}\n",
    )

    registry = build_registry([
        Path("zeta.pdf"),
        Path("alpha.pdf"),
        Path("middle.pdf"),
    ])

    assert [record["disclosure_path"] for record in registry] == [
        "alpha.pdf",
        "middle.pdf",
        "zeta.pdf",
    ]
