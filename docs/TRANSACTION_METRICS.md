# Transaction & Linkage Metrics Architecture

TransparencyX employs a strict, deterministic, and fail-closed architecture for parsing transactions and measuring asset linkages. This document outlines the technical design, terminology, and invariant constraints for Schedule B trading data.

## 1. Schedule B Parsing Constraints
Transaction extraction from Schedule B (or equivalent disclosure forms) operates under a purely deterministic paradigm. Inference, approximation, and assumptions are completely forbidden. If a record cannot be definitively extracted, the parser fails closed. No fuzzy matching algorithms are permitted at any stage of the pipeline.

## 2. Anchored Fields
A valid transaction row must contain completely anchored fields. Partial extraction or estimation is not supported.

## 3. Financial Trace Details
The summary layer operates exclusively over factual data surfaces provided by the pipeline trace. The trace structure exposes `detail_rows` containing purely objective, extracted values from the disclosure pipeline.

## 4. Transaction Type Labels
The `transaction_type_label` is implemented as an additive, human-readable enrichment. It supplements the original data without ever replacing or obscuring the underlying raw `transaction_type`.

## 5. Exact Key Asset Linkage
Linkage between a transaction and an asset is performed strictly using exact, normalized string keys. Fuzzy matching, heuristic alignment, and similarity thresholds are strictly forbidden. If an asset cannot be mathematically proven to match via its deterministic key, it is not linked.

## 6. Unlinked Ambiguity
Any ambiguous, mismatched, or missing asset data during the linkage process results in the transaction remaining unlinked. There is no partial linkage or confidence thresholding for transaction-to-asset mapping. 

## 7. Count Definitions
- **`linked_transaction_count`**: The explicit number of extracted transactions where `linked_asset_id` is definitively not `None`.
- **`unlinked_transaction_count`**: Computed strictly via subtraction: `transaction_count - linked_transaction_count`.

## 8. Transaction Coverage Ratio
- **`linked_transaction_coverage_ratio`**: A raw, unformatted float representing the proportion of transactions definitively tied to an asset (`linked_transaction_count / transaction_count`).

## 9. Mathematical Invariants
The summary generation layer enforces three unbreakable internal consistency invariants. If any are violated, the pipeline halts with a `ValueError`:
- `linked_transaction_count + unlinked_transaction_count == transaction_count` must always hold true.
- When `transaction_count > 0`, `linked_transaction_coverage_ratio` must exactly equal `linked_transaction_count / transaction_count`.
- When `transaction_count == 0`, `linked_transaction_coverage_ratio` must equal `None`.

## 10. Display Layer Directives
TransparencyX outputs are designed for objective consumption.
- The public HTML dossier and JSON serialization must remain 100% factual. 
- Words like "suspicious," "risk," "misconduct," "conflict," or "insider trading" are banned across the codebase.
- Metrics such as the coverage ratio must be presented as pure unformatted numbers, without arbitrary percentage formatting, rounding, or interpretative rankings.
