# NC 2023 Disclosure Acquisition Instructions

## Purpose

This document defines how to manually acquire missing disclosure PDFs for the NC 2023 acquisition plan.

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
   data/raw/house/2023/<document_id>.pdf
7. Update acquisition plan:
   - acquired = true
   - source_pdf = saved path
8. Re-run:
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
- Do not infer missing filings.
- Do not substitute alternate documents.
- If a filing is not found, leave entry unchanged.

## Notes

- Some members may file amendments.
