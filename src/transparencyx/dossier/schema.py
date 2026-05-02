from dataclasses import asdict, dataclass, field


@dataclass
class EvidenceSource:
    source_type: str
    source_name: str
    source_url: str | None = None
    retrieved_at: str | None = None
    notes: str | None = None


@dataclass
class MemberIdentity:
    member_id: str
    full_name: str
    chamber: str | None = None
    state: str | None = None
    district: str | None = None
    party: str | None = None
    current_status: str | None = None


@dataclass
class MemberOffice:
    official_salary: float | None = None
    leadership_roles: list[str] = field(default_factory=list)
    committee_assignments: list[str] = field(default_factory=list)
    office_start: str | None = None
    office_end: str | None = None


@dataclass
class DossierFinancials:
    disclosure_years: list[int] = field(default_factory=list)
    asset_count: int | None = None
    asset_value_min: float | None = None
    asset_value_max: float | None = None
    income_min: float | None = None
    income_max: float | None = None
    trade_count: int | None = None
    linked_transaction_coverage_ratio: float | None = None
    liability_count: int | None = None
    business_interests: list[str] = field(default_factory=list)


@dataclass
class DossierExposure:
    federal_award_exposure: list[dict] = field(default_factory=list)
    recipient_candidates: list[dict] = field(default_factory=list)
    exposure_counted: bool = False


@dataclass
class MemberDossier:
    identity: MemberIdentity
    office: MemberOffice
    financials: DossierFinancials
    exposure: DossierExposure
    evidence_sources: list[EvidenceSource] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def create_empty_member_dossier(member_id: str, full_name: str) -> MemberDossier:
    clean_member_id = member_id.strip()
    clean_full_name = full_name.strip()

    if not clean_member_id:
        raise ValueError("member_id is required")
    if not clean_full_name:
        raise ValueError("full_name is required")

    return MemberDossier(
        identity=MemberIdentity(
            member_id=clean_member_id,
            full_name=clean_full_name,
        ),
        office=MemberOffice(),
        financials=DossierFinancials(),
        exposure=DossierExposure(),
        evidence_sources=[],
    )
