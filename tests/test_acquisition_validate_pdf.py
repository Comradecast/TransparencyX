import sys

import pytest

from transparencyx.acquisition.validate_pdf import validate_disclosure_pdf


VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def test_valid_disclosure_pdf_passes(tmp_path):
    path = tmp_path / "10056549.pdf"
    path.write_bytes(VALID_PDF_BYTES)

    assert validate_disclosure_pdf(path, "10056549") is True


def test_wrong_filename_fails(tmp_path):
    path = tmp_path / "renamed.pdf"
    path.write_bytes(VALID_PDF_BYTES)

    assert validate_disclosure_pdf(path, "10056549") is False


def test_non_pdf_fails(tmp_path):
    path = tmp_path / "10056549.pdf"
    path.write_text("not a pdf", encoding="utf-8")

    assert validate_disclosure_pdf(path, "10056549") is False


def test_empty_file_fails(tmp_path):
    path = tmp_path / "10056549.pdf"
    path.write_bytes(b"")

    assert validate_disclosure_pdf(path, "10056549") is False


def test_mismatched_doc_id_fails(tmp_path):
    path = tmp_path / "10056549.pdf"
    path.write_bytes(VALID_PDF_BYTES)

    assert validate_disclosure_pdf(path, "10000000") is False


def test_pdf_header_without_eof_marker_fails(tmp_path):
    path = tmp_path / "10056549.pdf"
    path.write_bytes(b"%PDF-1.4\n")

    assert validate_disclosure_pdf(path, "10056549") is False


def test_cli_validate_pdf_success(tmp_path, monkeypatch, capsys):
    path = tmp_path / "10056549.pdf"
    path.write_bytes(VALID_PDF_BYTES)
    monkeypatch.setattr(
        sys,
        "argv",
        ["transparencyx", "--validate-pdf", str(path), "10056549"],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 0
    assert captured.out == "Disclosure PDF Validation: PASS\n"


def test_cli_validate_pdf_failure(tmp_path, monkeypatch, capsys):
    path = tmp_path / "10056549.pdf"
    path.write_text("not a pdf", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        ["transparencyx", "--validate-pdf", str(path), "10056549"],
    )

    from transparencyx.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main()

    captured = capsys.readouterr()
    assert exit_info.value.code == 1
    assert captured.out == "Disclosure PDF Validation: FAIL\n"
