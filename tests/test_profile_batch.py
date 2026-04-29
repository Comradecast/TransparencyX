from pathlib import Path

from transparencyx.profile.batch import build_profile_for_pdf, build_profiles_for_directory


def test_build_profiles_for_directory_finds_pdfs(tmp_path, monkeypatch):
    (tmp_path / "a.pdf").write_bytes(b"")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.pdf").write_bytes(b"")
    (tmp_path / "notes.txt").write_text("ignore")

    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profile_for_pdf",
        lambda pdf_path: {"disclosure_path": str(pdf_path)},
    )

    profiles = build_profiles_for_directory(tmp_path)

    assert len(profiles) == 2
    assert all(profile["disclosure_path"].endswith(".pdf") for profile in profiles)


def test_build_profiles_for_directory_deterministic_ordering(tmp_path, monkeypatch):
    (tmp_path / "z.pdf").write_bytes(b"")
    (tmp_path / "a.pdf").write_bytes(b"")
    (tmp_path / "m.pdf").write_bytes(b"")

    monkeypatch.setattr(
        "transparencyx.profile.batch.build_profile_for_pdf",
        lambda pdf_path: {"disclosure_path": pdf_path.name},
    )

    profiles = build_profiles_for_directory(tmp_path)

    assert [profile["disclosure_path"] for profile in profiles] == [
        "a.pdf",
        "m.pdf",
        "z.pdf",
    ]


def test_build_profile_for_pdf_contains_required_fields(monkeypatch):
    monkeypatch.setattr(
        "transparencyx.profile.batch._extract_text_from_pdf",
        lambda pdf_path: "Name: Hon. Nancy Pelosi\n",
    )
    monkeypatch.setattr(
        "transparencyx.profile.batch._build_shape_export_from_text",
        lambda pdf_path, extracted_text: {"politician_id": 1, "summary": {}, "trace": {}},
    )

    profile = build_profile_for_pdf(Path("sample.pdf"))

    assert profile == {
        "member_name": "Nancy Pelosi",
        "disclosure_path": "sample.pdf",
        "shape_export": {"politician_id": 1, "summary": {}, "trace": {}},
    }


def test_build_profiles_for_directory_empty_directory_returns_empty_list(tmp_path):
    assert build_profiles_for_directory(tmp_path) == []
