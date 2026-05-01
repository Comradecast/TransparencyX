# Member Metadata Expansion Plan

## Section 1 - Scope

- Target: Full coverage of current U.S. House (435) and Senate (100)
- Dataset type: Offline CSV (`data/seed/member_metadata_seed.csv`)
- Update model: Manual / curated updates from official sources

## Section 2 - Required Fields (Authoritative)

- `member_id`
  - deterministic slug
  - must match dossier builder

- `full_name`
  - exact official name

- `chamber`
  - House or Senate only

- `state`
  - 2-letter abbreviation

- `district`
  - required for House
  - blank for Senate

- `party`
  - as reported by source

- `current_status`
  - "current" default

- `official_salary`
  - default 174000 unless verified otherwise

- `leadership_roles`
  - only if explicitly confirmed

- `committee_assignments`
  - only if explicitly confirmed

- `office_start` / `office_end`
  - optional, must be source-backed

- `source_name` / `source_url`
  - REQUIRED for every row

## Section 3 - Approved Data Sources

House:
- https://clerk.house.gov/Members
- https://clerk.house.gov/Members/ViewMemberList

Senate:
- https://www.senate.gov/senators/
- https://www.senate.gov/states/

Rules:
- No Wikipedia as primary source
- No aggregation sites
- Cross-check allowed, but primary must be official

## Section 4 - Data Entry Rules

- No guessing
- No inferred committees
- No inferred leadership roles
- Blank > wrong data
- Every row must have provenance

## Section 5 - Update Workflow

1. Copy template CSV
2. Add or update rows from official source
3. Ensure source_name + source_url populated
4. Run:
   `python -m transparencyx --validate-member-metadata-seed data/seed/member_metadata_seed.csv`
5. Fix all errors
6. Commit with message:
   `"Update member metadata seed (N records)"`

## Section 6 - Validation Requirements

Must pass:

- No duplicate member_id
- No missing required fields
- All rows have source_name or source_url
- House/Senate counts match expectations
- Salary parses as float

## Section 7 - Expansion Targets

- Phase 1: All NC delegation (done)
- Phase 2: Full House
- Phase 3: Full Senate
- Phase 4: Verified committees (optional)
- Phase 5: Verified leadership roles (optional)

## Section 8 - Known Limitations

- Committee data incomplete unless verified
- Leadership roles incomplete unless verified
- No historical membership tracking yet
- No automated updates

## Section 9 - Future Extensions (NOT IMPLEMENTED)

- Committee overlap with spending
- Leadership role weighting
- Timeline alignment with trades/exposure
- Historical membership tracking
