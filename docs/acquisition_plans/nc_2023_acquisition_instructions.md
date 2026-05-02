# NC 2023 Disclosure Acquisition Instructions

## Purpose

This document defines how to manually acquire missing disclosure PDFs for the NC 2023 acquisition plan.

Use the index acquisition manifest to identify known DocIDs:
docs/acquisition_plans/nc_2023_index_acquisition_manifest.json

## Source of truth

The authoritative source is the official House/Senate financial disclosure system.

## Acquisition steps

For each member:

1. Navigate to official disclosure search site:
   https://disclosures-clerk.house.gov/PublicDisclosure/FinancialDisclosure
2. Search by:
   - Last name
   - Filing year: 2023
3. Locate:
   - Annual Financial Disclosure Report
4. Verify:
   - Correct member
   - Correct filing year
   - PDF format
5. Download PDF
6. Save locally as:
   data/raw/house/2023/<DocID>.pdf
   - Use the exact document ID provided by the disclosure system.
   - Use the exact filename format `<DocID>.pdf`.
   - Do not rename or shorten the file name.
7. Validate PDF:
   python -m transparencyx --validate-pdf data/raw/house/2023/<DocID>.pdf <DocID>
   - Accept the PDF only if validation returns PASS.
   - If validation returns FAIL, do not mark acquired.
   - If validation returns FAIL, do not update source_pdf.
   - If validation returns FAIL, leave the acquisition entry unchanged.
   - If validation returns FAIL, record a neutral note if needed.
8. Update acquisition plan:
   - acquired = true
   - source_pdf = saved path
9. Re-run:
   - dataset build and validation

## Members requiring acquisition

- donald-g-davis
- gregory-f-murphy
- addison-p-mcdowell
- david-rouzer
- mark-harris
- richard-hudson
- pat-harrigan
- brad-knott
- tim-moore
- ted-budd
- thom-tillis

## Constraints

- Do not rename files arbitrarily.
- Use `<DocID>.pdf`; no renaming and no shortened names.
- Do not infer missing filings.
- Do not substitute alternate documents.
- If a filing is not found, leave entry unchanged.

## Notes

- Some members may file amendments.
