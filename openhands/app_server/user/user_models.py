from openhands.integrations.provider import PROVIDER_TOKEN_TYPE
from openhands.storage.data_models.settings import Settings


class UserInfo(Settings):
    """Model for user settings including the current user id."""

    id: str | None = None
    is_org_admin: bool = False


class ProviderTokenPage:
    items: list[PROVIDER_TOKEN_TYPE]
    next_page_id: str | None = None
