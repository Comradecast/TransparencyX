from pathlib import Path


def render_site_readme(demo_dataset: str | None = None) -> str:
    demo_section = ""
    if demo_dataset:
        demo_section = f"""Demo Dataset:
- {demo_dataset}

"""

    return f"""TransparencyX Generated Dossier Site

This folder contains generated TransparencyX dossier site artifacts.

{demo_section}\
Artifacts:
- index.html is the static browser entry point.
- index.json is the machine-readable dossier index.
- build_manifest.json records build inputs, enabled options, counts, and generated artifacts.
- metadata_coverage.json exists only when member metadata was provided.
- Individual .json files contain canonical member dossier data.
- Individual .html files contain static member dossier pages.

Open:
- Open index.html in a browser to view the generated local site.

Data Notes and Limitations:
- Federal award exposure rows are exact fetched exposure results.
- Recipient candidate rows are review-only and are not counted as exposure.
- The site presents structured public-record data and does not make accusations or legal conclusions.
"""


def write_site_readme(
    output_dir: str | Path,
    demo_dataset: str | None = None,
) -> Path:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "README.txt"
    path.write_text(render_site_readme(demo_dataset), encoding="utf-8")
    return path
