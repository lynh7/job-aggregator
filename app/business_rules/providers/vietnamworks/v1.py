from app.business_rules.passthrough import PassThroughRules


class VietnamWorksV1Rules(PassThroughRules):
    """VietnamWorks API v1 rule slot. Raw pass-through until mappings are defined."""

    def __init__(self) -> None:
        super().__init__(provider="vietnamworks", api_version="v1")

