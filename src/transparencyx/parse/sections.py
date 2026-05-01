"""
Section detection and segmentation.
"""
from dataclasses import dataclass
from typing import List


@dataclass
class Section:
    """
    Represents a segmented logical block of text from a disclosure.
    """
    name: str
    start_index: int
    end_index: int
    raw_text: str


# Predefined section markers we look for
KNOWN_HEADERS = [
    "SCHEDULE A",
    "ASSETS",
    "SCHEDULE B",
    "S B: T",
    "INCOME",
    "LIABILITIES",
    "POSITIONS",
    "AGREEMENTS"
]

ASSET_COLUMN_HEADER = "ASSET OWNER VALUE OF ASSET INCOME TYPE(S)"

def detect_sections(text: str) -> List[Section]:
    """
    Segments raw text into major disclosure sections based on simple keyword detection.
    Does not interpret the content, only segments the raw text block.
    """
    if not text:
        return []

    # Find the positions of all known headers
    found_headers = []
    text_upper = text.upper()
    asset_column_header_pos = text_upper.find(ASSET_COLUMN_HEADER)
    
    for header in KNOWN_HEADERS:
        # Simple substring search.
        # This could be improved later (e.g. word boundaries), but keeps things simple for now.
        if header == "ASSETS" and asset_column_header_pos != -1:
            start_pos = asset_column_header_pos
        else:
            start_pos = text_upper.find(header)
        if start_pos != -1:
            found_headers.append({
                "name": header,
                "start_index": start_pos
            })
            
    # If no headers found, return the whole text as "UNCLASSIFIED"
    if not found_headers:
        return [
            Section(
                name="UNCLASSIFIED",
                start_index=0,
                end_index=len(text),
                raw_text=text
            )
        ]

    # Sort found headers by their appearance in the text
    found_headers.sort(key=lambda x: x["start_index"])

    # Deduplicate: if multiple headers appear on the same line, keep only the first
    # when it has a strictly longer keyword. This prevents header text like
    # 'Schedule A: Assets and "Unearned" Income' from being split into
    # separate SCHEDULE A / ASSETS / INCOME sections, while still allowing
    # two equal-length keywords on the same line to remain separate.
    deduplicated = []
    for header in found_headers:
        pos = header["start_index"]
        # Find the line boundaries for this header's position
        line_start = text.rfind("\n", 0, pos) + 1
        line_end = text.find("\n", pos)
        if line_end == -1:
            line_end = len(text)

        # Skip if a previously kept header with a strictly longer keyword
        # starts on the same line
        skip = False
        for kept in deduplicated:
            if line_start <= kept["start_index"] < line_end:
                if kept["name"] == "ASSETS" and kept["start_index"] == asset_column_header_pos:
                    skip = True
                    break
                if len(kept["name"]) > len(header["name"]):
                    skip = True
                    break
        if not skip:
            deduplicated.append(header)

    found_headers = deduplicated
    sections = []
    
    # Process each found header and slice until the next header (or end of text)
    for i, current_header in enumerate(found_headers):
        start_idx = current_header["start_index"]
        
        # If there's another header after this one, slice up to it
        if i + 1 < len(found_headers):
            end_idx = found_headers[i + 1]["start_index"]
        else:
            # Otherwise, slice to the end of the text
            end_idx = len(text)
            
        section_text = text[start_idx:end_idx].strip()
        
        sections.append(
            Section(
                name=current_header["name"],
                start_index=start_idx,
                end_index=end_idx,
                raw_text=section_text
            )
        )

    return sections
