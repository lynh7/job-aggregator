from app.business_rules.passthrough import PassThroughRules


class MockV1Rules(PassThroughRules):
    def __init__(self) -> None:
        super().__init__(provider="mock", api_version="v1")

