from app.business_rules.passthrough import PassThroughRules


class TopCVV1Rules(PassThroughRules):
    """TopCV API v1 rule slot. Raw pass-through until mappings are defined."""

    def __init__(self) -> None:
        super().__init__(provider="topcv", api_version="v1")

