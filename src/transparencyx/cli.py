import argparse
import sys
import json
from importlib.metadata import version, PackageNotFoundError
import datetime
from pathlib import Path

from transparencyx.ranges import parse_range
from transparencyx.sources.registry import get_registered_sources
from transparencyx.sources.downloader import Downloader
from transparencyx.extract.registry import get_extractor_for_source
from transparencyx.config import RAW_DATA_DIR
from transparencyx.parse.sections import detect_sections
from transparencyx.db.database import initialize_database, get_connection
from transparencyx.ingest.house import HouseDisclosureRecord, insert_house_raw_disclosure
from transparencyx.normalize.assets import process_assets_for_disclosure


def get_normalized_asset_audit_rows(db_path: Path):
    """
    Returns normalized asset rows in deterministic insertion order for audit output.
    """
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id,
                asset_name,
                asset_category,
                original_value_range,
                value_min,
                value_max,
                value_midpoint
            FROM normalized_assets
            ORDER BY id ASC
            """
        )
        return [dict(row) for row in cursor.fetchall()]


def format_normalized_asset_audit_table(rows) -> str:
    """
    Formats normalized asset rows as a deterministic audit table.
    """
    columns = [
        "id",
        "asset_name",
        "asset_category",
        "original_value_range",
        "value_min",
        "value_max",
        "value_midpoint",
    ]
    lines = [" | ".join(columns)]

    for row in rows:
        lines.append(" | ".join("" if row[column] is None else str(row[column]) for column in columns))

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="TransparencyX: A Python civic-data project that consolidates U.S. congressional financial disclosure information."
    )
    
    parser.add_argument(
        "--version", 
        action="store_true", 
        help="Show the version and exit."
    )
    parser.add_argument("--build-registry", type=str, help="Build a member registry from PDFs in a directory")
    parser.add_argument("--batch-profile", type=str, help="Build profile exports from PDFs in a directory")
    parser.add_argument("--batch-summary", type=str, help="Build a compact profile summary table from PDFs in a directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # "sources" command and its subcommands
    sources_parser = subparsers.add_parser("sources", help="Manage data sources")
    sources_subparsers = sources_parser.add_subparsers(dest="sources_command", help="Source operations")
    
    # "sources list"
    sources_subparsers.add_parser("list", help="List supported sources")
    
    # "sources fetch"
    fetch_parser = sources_subparsers.add_parser("fetch", help="Simulate fetching source disclosures")
    fetch_group = fetch_parser.add_mutually_exclusive_group(required=True)
    fetch_group.add_argument("--all", action="store_true", help="Fetch from all available sources")
    fetch_group.add_argument("--chamber", choices=["house", "senate"], help="Fetch for a specific chamber")
    
    fetch_parser.add_argument("--year", type=int, default=datetime.datetime.now().year - 1, help="The disclosure year to fetch")

    # "extract" command
    extract_parser = subparsers.add_parser("extract", help="Extract text from downloaded disclosures")
    extract_group = extract_parser.add_mutually_exclusive_group(required=True)
    extract_group.add_argument("--all", action="store_true", help="Extract all downloaded files")
    extract_group.add_argument("--chamber", choices=["house", "senate"], help="Extract for a specific chamber")
    extract_parser.add_argument("--show-sections", action="store_true", help="Include detected text sections in output")

    # "db" command
    db_parser = subparsers.add_parser("db", help="Database operations")
    db_subparsers = db_parser.add_subparsers(dest="db_command", help="DB operations")
    db_init_parser = db_subparsers.add_parser("init", help="Initialize the SQLite database")
    db_init_parser.add_argument("--path", type=str, required=True, help="Path to the SQLite database file")

    # "ingest" command
    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw data")
    ingest_subparsers = ingest_parser.add_subparsers(dest="ingest_command", help="Ingest operations")
    ingest_house_parser = ingest_subparsers.add_parser("house-sample", help="Ingest a sample House disclosure")
    ingest_house_parser.add_argument("--db", type=str, required=True, help="Path to the SQLite database file")
    ingest_trades_parser = ingest_subparsers.add_parser("trades-sample", help="Ingest sample trades")
    ingest_trades_parser.add_argument("--db", type=str, required=True, help="Path to the SQLite database file")

    # "normalize" command
    normalize_parser = subparsers.add_parser("normalize", help="Normalize data")
    normalize_subparsers = normalize_parser.add_subparsers(dest="normalize_command", help="Normalize operations")
    normalize_assets_parser = normalize_subparsers.add_parser("assets", help="Normalize assets from raw text")
    normalize_assets_parser.add_argument("--db", type=str, required=True, help="Path to the SQLite database file")


    # "parse-range" command
    parse_parser = subparsers.add_parser("parse-range", help="Parse a financial disclosure range label")
    parse_parser.add_argument(
        "label", 
        type=str, 
        help="The range label to parse (e.g., '$1,001 - $15,000')"
    )

    # "shape" command
    shape_parser = subparsers.add_parser("shape", help="Shape model operations")
    shape_subparsers = shape_parser.add_subparsers(dest="shape_command", help="Shape commands")
    shape_summary_parser = shape_subparsers.add_parser("summary", help="Build a financial shape summary")
    shape_summary_parser.add_argument("--db", type=str, required=True, help="Path to the SQLite database file")
    shape_summary_parser.add_argument("--politician-id", type=int, required=True, help="ID of the politician")

    # "demo-run" command
    subparsers.add_parser("demo-run", help="Run a demo: create a sample database and produce a shape export")

    # "validate-real" command
    validate_parser = subparsers.add_parser("validate-real", help="Validate one real disclosure through the full pipeline")
    validate_parser.add_argument("--pdf", type=str, required=True, help="Path to a real House disclosure PDF")
    validate_parser.add_argument("--show-assets", action="store_true", help="Print normalized asset rows for audit")
    validate_parser.add_argument("--shape-card", action="store_true", help="Print a human-readable financial shape card")
    validate_parser.add_argument("--profile-card", action="store_true", help="Print a human-readable member profile card")
    validate_parser.add_argument("--fetch-exposure", action="store_true", help="Fetch federal award exposure for disclosed business interests")
    validate_parser.add_argument("--compare", nargs=2, metavar=("A", "B"))

    args = parser.parse_args()
    
    if args.version:
        try:
            pkg_version = version("transparencyx")
            print(f"transparencyx version {pkg_version}")
        except PackageNotFoundError:
            print("transparencyx version unknown (not installed)")
        sys.exit(0)

    if args.build_registry:
        from transparencyx.profile.registry import build_registry

        registry_dir = Path(args.build_registry)
        pdf_paths = list(registry_dir.rglob("*.pdf"))
        print(json.dumps(build_registry(pdf_paths), indent=2))
        sys.exit(0)

    if args.batch_profile:
        from transparencyx.profile.batch import build_profiles_for_directory

        print(json.dumps(build_profiles_for_directory(Path(args.batch_profile)), indent=2))
        sys.exit(0)

    if args.batch_summary:
        from transparencyx.profile.batch import build_profiles_for_directory
        from transparencyx.profile.table import render_batch_summary_table

        profiles = build_profiles_for_directory(Path(args.batch_summary))
        print(render_batch_summary_table(profiles))
        sys.exit(0)
        
    if args.command == "sources":
        if args.sources_command == "list":
            sources = get_registered_sources()
            for chamber in sources.keys():
                print(chamber)
        elif args.sources_command == "fetch":
            downloader = Downloader()
            paths = []
            if args.all:
                paths = downloader.fetch_all(args.year)
            elif args.chamber:
                paths = downloader.fetch_chamber(args.chamber, args.year)
            
            for path in paths:
                print(f"Fetched (placeholder): {path}")
        else:
            sources_parser.print_help()
            
    elif args.command == "extract":
        search_dir = RAW_DATA_DIR
        
        # Determine the target directory based on the chamber argument
        if args.chamber:
            search_dir = RAW_DATA_DIR / args.chamber.lower()
            
        if not search_dir.exists():
            print(f"No raw data directory found at {search_dir}")
            sys.exit(0)
            
        sources_dict = get_registered_sources()
        results = []
        
        # Iterate over files in the target directory (recursive)
        for file_path in search_dir.rglob("*"):
            if file_path.is_file():
                # Derive file type from extension without the leading dot
                file_ext = file_path.suffix.lstrip(".")
                
                chamber_name = "unknown"
                try:
                    rel_path = file_path.relative_to(RAW_DATA_DIR)
                    chamber_name = rel_path.parts[0]
                except ValueError:
                    pass
                
                source = sources_dict.get(chamber_name)
                
                if not source:
                    results.append({
                        "file_path": str(file_path),
                        "source": chamber_name,
                        "success": False,
                        "error": f"Unknown source directory: {chamber_name}"
                    })
                    continue
                
                extractor = get_extractor_for_source(source, file_ext)
                if extractor:
                    result = extractor.extract(file_path, source)
                    if result.success:
                        length = len(result.extracted_text) if result.extracted_text else 0
                        
                        out = {
                            "file_path": str(result.file_path),
                            "source": result.source.chamber_name,
                            "success": True,
                            "extracted_length": length
                        }
                        
                        if args.show_sections and result.extracted_text:
                            sections = detect_sections(result.extracted_text)
                            out["sections"] = [
                                {
                                    "name": sec.name,
                                    "start_index": sec.start_index,
                                    "end_index": sec.end_index,
                                    "length": len(sec.raw_text)
                                }
                                for sec in sections
                            ]
                            
                        results.append(out)
                    else:
                        results.append({
                            "file_path": str(result.file_path),
                            "source": result.source.chamber_name,
                            "success": False,
                            "error": result.error
                        })
                else:
                    results.append({
                        "file_path": str(file_path),
                        "source": source.chamber_name,
                        "success": False,
                        "error": f"No extractor found for file type: {file_ext}"
                    })
                    
        print(json.dumps(results, indent=2))
        
    elif args.command == "db":
        if args.db_command == "init":
            db_path = Path(args.path)
            initialize_database(db_path)
            print(f"Database initialized at {db_path}")
        else:
            db_parser.print_help()
            
    elif args.command == "ingest":
        if args.ingest_command == "house-sample":
            db_path = Path(args.db)
            record = HouseDisclosureRecord(
                filing_year=2023,
                document_title="Financial Disclosure Report",
                document_url="https://disclosures-clerk.house.gov/public_disc/financial-pdfs/2023/1234567.pdf",
                politician_name="Doe, John",
                filing_type="Annual",
                local_path="data/raw/house/2023/1234567.pdf"
            )
            record_id = insert_house_raw_disclosure(db_path, record)
            print(json.dumps({"success": True, "record_id": record_id}, indent=2))
        elif args.ingest_command == "trades-sample":
            db_path = Path(args.db)
            initialize_database(db_path)
            from transparencyx.ingest.trades import ingest_sample_trades
            with get_connection(db_path) as conn:
                inserted = ingest_sample_trades(conn)
            print(json.dumps({"success": True, "inserted_count": inserted}, indent=2))
        else:
            ingest_parser.print_help()

    elif args.command == "normalize":
        if args.normalize_command == "assets":
            db_path = Path(args.db)
            sources_dict = get_registered_sources()
            processed_count = 0
            total_inserted = 0
            
            with get_connection(db_path) as conn:
                cursor = conn.cursor()
                # Get raw disclosures with a local_path
                cursor.execute(
                    "SELECT id, politician_id, local_path, source_chamber FROM raw_disclosures WHERE local_path IS NOT NULL"
                )
                rows = cursor.fetchall()
                
            for row in rows:
                raw_id = row["id"]
                politician_id = row["politician_id"]
                local_path = Path(row["local_path"])
                chamber = row["source_chamber"]
                
                # We need a dummy politician_id to satisfy constraints if it's NULL in the raw row,
                # but the instructions say politician_id is NOT NULL in normalized_assets, and might be NULL in raw_disclosures.
                # So if politician_id is missing, we must skip or handle it.
                if politician_id is None:
                    # In a real pipeline, we'd resolve the politician first. For now, skip or use a dummy ID.
                    # Let's skip for safety.
                    continue
                
                if not local_path.exists():
                    continue
                    
                source = sources_dict.get(chamber)
                if not source:
                    continue
                    
                file_ext = local_path.suffix.lstrip(".")
                extractor = get_extractor_for_source(source, file_ext)
                
                if extractor:
                    result = extractor.extract(local_path, source)
                    if result.success and result.extracted_text:
                        inserted = process_assets_for_disclosure(
                            db_path=db_path,
                            raw_disclosure_id=raw_id,
                            politician_id=politician_id,
                            extracted_text=result.extracted_text
                        )
                        processed_count += 1
                        total_inserted += inserted
                        
            print(json.dumps({
                "processed": processed_count,
                "inserted_assets": total_inserted
            }, indent=2))
        else:
            normalize_parser.print_help()

    elif args.command == "parse-range":
        parsed = parse_range(args.label)
        
        output = {
            "label": parsed.original_label,
            "minimum": parsed.minimum,
            "maximum": parsed.maximum,
            "midpoint": parsed.midpoint,
        }
        
        print(json.dumps(output, indent=2))
        
    elif args.command == "shape":
        if args.shape_command == "summary":
            db_path = Path(args.db)
            politician_id = args.politician_id
            
            from transparencyx.shape.summary import build_financial_shape_summary, summary_to_dict
            
            summary = build_financial_shape_summary(db_path, politician_id)
            print(json.dumps(summary_to_dict(summary), indent=2))
        else:
            shape_parser.print_help()
    elif args.command == "demo-run":
        from transparencyx.demo import run_demo

        db_path = Path("data/demo.sqlite")
        export = run_demo(db_path)
        print(json.dumps(export, indent=2))
    elif args.command == "validate-real":
        from transparencyx.shape.export import build_financial_shape_export
        from transparencyx.shape.card import render_financial_shape_card
        from transparencyx.shape.compare import render_shape_comparison
        from transparencyx.profile.card import render_member_profile_card
        from transparencyx.profile.identity import extract_member_identity
        from transparencyx.spending.fetch import fetch_award_exposure
        from transparencyx.spending.linker import link_business_interests_to_award_exposure

        pdf_path = Path(args.pdf)
        if not pdf_path.exists():
            print(f"PDF not found: {pdf_path}")
            sys.exit(1)

        quiet = args.shape_card or args.profile_card or args.fetch_exposure or args.compare

        def build_validate_real_export(politician_id: int, db_path: Path) -> tuple[dict, Path, dict]:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            if db_path.exists():
                db_path.unlink()

            initialize_database(db_path)

            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            with get_connection(db_path) as conn:
                cursor = conn.cursor()

                # 1. Insert politician
                cursor.execute("""
                    INSERT INTO politicians
                        (id, first_name, last_name, full_name, chamber, created_at, updated_at)
                    VALUES (?, 'Real', 'Disclosure', 'Disclosure, Real', 'house', ?, ?)
                """, (politician_id, now, now))

                # 2. Insert raw disclosure pointing at the real PDF
                cursor.execute("""
                    INSERT INTO raw_disclosures
                        (id, politician_id, source_chamber, source_name, filing_year,
                         retrieved_at, raw_metadata_json, local_path, created_at)
                    VALUES (1, ?, 'house', 'validate-real', 2023, ?, '{}', ?, ?)
                """, (politician_id, now, str(pdf_path), now))

                conn.commit()

            # 3. Extract text from the PDF
            sources_dict = get_registered_sources()
            source = sources_dict.get("house")
            file_ext = pdf_path.suffix.lstrip(".")
            extractor = get_extractor_for_source(source, file_ext)

            if not extractor:
                print(f"No extractor for file type: {file_ext}")
                sys.exit(1)

            result = extractor.extract(pdf_path, source)
            if not result.success:
                print(json.dumps({"success": False, "error": result.error}, indent=2))
                sys.exit(1)

            identity = extract_member_identity(result.extracted_text)

            if not quiet:
                print(f"Extracted {len(result.extracted_text)} chars from PDF")

            # 4. Show section detection
            sections = detect_sections(result.extracted_text)
            if not quiet:
                print(f"Sections detected: {[s.name for s in sections]}")

            # 5. Normalize assets
            inserted = process_assets_for_disclosure(
                db_path=db_path,
                raw_disclosure_id=1,
                politician_id=politician_id,
                extracted_text=result.extracted_text
            )
            if not quiet:
                print(f"Normalized assets inserted: {inserted}")

            # 6. Build shape export
            return build_financial_shape_export(db_path, politician_id), db_path, identity

        def build_validate_real_profile(shape_export: dict, identity: dict) -> dict:
            return {
                "member_name": identity.get("member_name", "Unknown"),
                "politician_id": 1,
                "filing_year": 2023,
                "source": "validate-real",
                "disclosure_path": str(pdf_path),
                "shape_export": shape_export,
            }

        if args.compare:
            politician_a = int(args.compare[0])
            politician_b = int(args.compare[1])
            export_a, _, _ = build_validate_real_export(politician_a, Path("data/validate_real_compare_a.sqlite"))
            export_b, _, _ = build_validate_real_export(politician_b, Path("data/validate_real_compare_b.sqlite"))
            print(render_shape_comparison(export_a, export_b))
        else:
            export, db_path, identity = build_validate_real_export(1, Path("data/validate_real.sqlite"))
            if args.shape_card:
                print(render_financial_shape_card(export))
            elif args.profile_card:
                print(render_member_profile_card(build_validate_real_profile(export, identity)))
            elif args.fetch_exposure:
                rows = get_normalized_asset_audit_rows(db_path)
                links = link_business_interests_to_award_exposure(rows)
                print(json.dumps([fetch_award_exposure(link) for link in links], indent=2))
            else:
                print(json.dumps(export, indent=2))

        if args.show_assets and not quiet:
            rows = get_normalized_asset_audit_rows(db_path)
            print(format_normalized_asset_audit_table(rows))
    elif args.command is None:
        parser.print_help()

if __name__ == "__main__":
    main()
