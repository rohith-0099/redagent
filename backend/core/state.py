"""In-memory campaign store.

TODO: swap for Firestore in a later slice (CLAUDE.md section 5). Keep the
create/get/update surface so the swap is drop-in.
"""

from core.contracts import Campaign


class CampaignStore:
    def __init__(self) -> None:
        self._store: dict[str, Campaign] = {}

    def create(self, campaign: Campaign) -> Campaign:
        self._store[campaign.campaign_id] = campaign
        return campaign

    def get(self, campaign_id: str) -> Campaign | None:
        return self._store.get(campaign_id)

    def update(self, campaign: Campaign) -> Campaign:
        if campaign.campaign_id not in self._store:
            raise KeyError(campaign.campaign_id)
        self._store[campaign.campaign_id] = campaign
        return campaign
