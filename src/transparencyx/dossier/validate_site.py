import json
from html.parser import HTMLParser
from pathlib import Path


REQUIRED_FILES = [
    "index.html",
    "index.json",
    "build_manifest.json",
    "README.txt",
]


class _HrefParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        for name, value in attrs:
            if name == "href" and value is not None:
                self.hrefs.append(value)


def _load_json(path: Path, label: str, errors: list[str]):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        errors.append(f"{label} is not valid JSON")
    except OSError as error:
        errors.append(f"{label} could not be read: {error}")
    return None


def _is_external_href(href: str) -> bool:
    return "://" in href or href.startswith("mailto:")


def _check_artifact(output_path: Path, filename, label: str, errors: list[str]) -> None:
    if filename is None:
        return
    if not isinstance(filename, str) or not filename:
        errors.append(f"build_manifest.json has invalid artifact entry: {label}")
        return
    if not (output_path / filename).exists():
        errors.append(f"build_manifest.json references missing file: {filename}")


def validate_dossier_site(output_dir: str | Path) -> dict:
    output_path = Path(output_dir)
    errors = []
    required_files = {filename: False for filename in REQUIRED_FILES}
    checked_index_json_files = 0
    checked_html_links = 0
    json_dossiers = 0
    html_dossiers = 0

    if not output_path.exists() or not output_path.is_dir():
        errors.append(f"output_dir is not a directory: {output_path}")
        return {
            "passed": False,
            "output_dir": str(output_path),
            "required_files": required_files,
            "json_dossiers": 0,
            "html_dossiers": 0,
            "checked_index_json_files": 0,
            "checked_html_links": 0,
            "errors": errors,
        }

    for filename in REQUIRED_FILES:
        exists = (output_path / filename).exists()
        required_files[filename] = exists
        if not exists:
            errors.append(f"missing required file: {filename}")

    index = None
    if required_files["index.json"]:
        index = _load_json(output_path / "index.json", "index.json", errors)
    if isinstance(index, dict):
        seen_files = set()
        dossiers = index.get("dossiers", [])
        if isinstance(dossiers, list):
            for row in dossiers:
                if not isinstance(row, dict):
                    continue
                filename = row.get("file")
                if not isinstance(filename, str) or not filename:
                    continue
                checked_index_json_files += 1
                if filename in seen_files:
                    errors.append(f"index.json duplicate dossier file reference: {filename}")
                seen_files.add(filename)
                if not (output_path / filename).exists():
                    errors.append(f"index.json references missing file: {filename}")

    if required_files["index.html"]:
        try:
            parser = _HrefParser()
            parser.feed((output_path / "index.html").read_text(encoding="utf-8"))
            local_html_hrefs = [
                href
                for href in parser.hrefs
                if href.endswith(".html") and not _is_external_href(href)
            ]
            checked_html_links = len(local_html_hrefs)
            for href in local_html_hrefs:
                if not (output_path / href).exists():
                    errors.append(f"index.html references missing file: {href}")
        except OSError as error:
            errors.append(f"index.html could not be read: {error}")

    manifest = None
    if required_files["build_manifest.json"]:
        manifest = _load_json(
            output_path / "build_manifest.json",
            "build_manifest.json",
            errors,
        )
    if isinstance(manifest, dict):
        artifacts = manifest.get("artifacts", {})
        counts = manifest.get("counts", {})
        if isinstance(artifacts, dict):
            _check_artifact(output_path, artifacts.get("json_index"), "json_index", errors)
            _check_artifact(output_path, artifacts.get("html_index"), "html_index", errors)
            _check_artifact(
                output_path,
                artifacts.get("metadata_coverage"),
                "metadata_coverage",
                errors,
            )
            dossier_json_files = artifacts.get("dossier_json_files", [])
            dossier_html_files = artifacts.get("dossier_html_files", [])
            if isinstance(dossier_json_files, list):
                json_dossiers = len(dossier_json_files)
                for filename in dossier_json_files:
                    _check_artifact(output_path, filename, "dossier_json_files", errors)
            if isinstance(dossier_html_files, list):
                html_dossiers = len(dossier_html_files)
                for filename in dossier_html_files:
                    _check_artifact(output_path, filename, "dossier_html_files", errors)
            if isinstance(counts, dict):
                if counts.get("json_dossiers") != json_dossiers:
                    errors.append("build_manifest.json json_dossiers count does not match listed files")
                if counts.get("html_dossiers") != html_dossiers:
                    errors.append("build_manifest.json html_dossiers count does not match listed files")

    metadata_coverage_path = output_path / "metadata_coverage.json"
    if metadata_coverage_path.exists():
        _load_json(metadata_coverage_path, "metadata_coverage.json", errors)

    return {
        "passed": len(errors) == 0,
        "output_dir": str(output_path),
        "required_files": required_files,
        "json_dossiers": json_dossiers,
        "html_dossiers": html_dossiers,
        "checked_index_json_files": checked_index_json_files,
        "checked_html_links": checked_html_links,
        "errors": errors,
    }


def render_dossier_site_validation(report: dict) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        f"Site Validation: {status}",
        f"- json dossiers: {report['json_dossiers']}",
        f"- html dossiers: {report['html_dossiers']}",
        f"- index.json dossier files checked: {report['checked_index_json_files']}",
        f"- index.html links checked: {report['checked_html_links']}",
    ]
    if report["errors"]:
        lines.extend(["", "errors:"])
        lines.extend(f"- {error}" for error in report["errors"])
    return "\n".join(lines) + "\n"
