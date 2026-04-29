from transparencyx.profile.identity import extract_member_identity


def test_extract_member_identity_from_house_name_line():
    identity = extract_member_identity("""
F I
Name: Hon. Nancy Pelosi
Status: Member
State/District: CA11
""")

    assert identity == {"member_name": "Nancy Pelosi"}


def test_extract_member_identity_collapses_whitespace():
    identity = extract_member_identity("Name:   Hon.   Jane   Q.   Member   \n")

    assert identity == {"member_name": "Jane Q. Member"}


def test_extract_member_identity_without_honorific():
    identity = extract_member_identity("Name: Jane Doe\n")

    assert identity == {"member_name": "Jane Doe"}


def test_extract_member_identity_returns_unknown_when_absent():
    identity = extract_member_identity("Status: Member\nState/District: CA11\n")

    assert identity == {"member_name": "Unknown"}


def test_extract_member_identity_returns_unknown_for_blank_name():
    identity = extract_member_identity("Name:   \nStatus: Member\n")

    assert identity == {"member_name": "Unknown"}
