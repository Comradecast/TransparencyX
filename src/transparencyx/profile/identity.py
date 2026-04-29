import re


def extract_member_identity(extracted_text: str) -> dict:
    match = re.search(r"^Name:[^\S\r\n]*(.*?)[^\S\r\n]*$", extracted_text, re.MULTILINE)
    if not match:
        return {"member_name": "Unknown"}

    member_name = " ".join(match.group(1).split())
    if member_name.startswith("Hon. "):
        member_name = member_name[5:].strip()

    if not member_name:
        return {"member_name": "Unknown"}

    return {"member_name": member_name}
