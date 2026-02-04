from pydantic import SecretStr

from openhands.integrations.azure_devops.azure_devops_service import (
    AzureDevOpsServiceImpl as AzureDevOpsService,
)
from openhands.integrations.bitbucket.bitbucket_service import BitBucketService
from openhands.integrations.forgejo.forgejo_service import ForgejoService
from openhands.integrations.github.github_service import GitHubService
from openhands.integrations.gitlab.gitlab_service import GitLabService
from openhands.integrations.provider import ProviderType


async def validate_provider_token(
    token: SecretStr,
    base_domain: str | None = None,
    expected_provider: ProviderType | None = None,
) -> ProviderType | None:
    """Determine whether a token is for GitHub, GitLab, Bitbucket, Forgejo, or Azure DevOps.

    When expected_provider is provided (e.g. when saving from the Git settings UI), only
    validates against that provider. Otherwise tries each provider in sequence to detect
    the token type.

    Args:
        token: The token to check
        base_domain: Optional base domain for the service
        expected_provider: When set, only validate against this provider (avoids
            unnecessary API calls and log warnings when the provider is known)

    Returns:
        The provider type if valid, None if invalid
    """
    # Skip validation for empty tokens
    if token is None:
        return None  # type: ignore[unreachable]

    async def try_github() -> ProviderType | None:
        try:
            github_service = GitHubService(token=token, base_domain=base_domain)
            await github_service.verify_access()
            return ProviderType.GITHUB
        except Exception:
            return None

    async def try_gitlab() -> ProviderType | None:
        try:
            gitlab_service = GitLabService(token=token, base_domain=base_domain)
            await gitlab_service.get_user()
            return ProviderType.GITLAB
        except Exception:
            return None

    async def try_forgejo() -> ProviderType | None:
        if not base_domain:
            return None
        try:
            forgejo_service = ForgejoService(token=token, base_domain=base_domain)
            await forgejo_service.get_user()
            return ProviderType.FORGEJO
        except Exception:
            return None

    async def try_bitbucket() -> ProviderType | None:
        try:
            bitbucket_service = BitBucketService(token=token, base_domain=base_domain)
            await bitbucket_service.get_user()
            return ProviderType.BITBUCKET
        except Exception:
            return None

    async def try_azure_devops() -> ProviderType | None:
        try:
            azure_devops_service = AzureDevOpsService(
                token=token, base_domain=base_domain
            )
            await azure_devops_service.get_user()
            return ProviderType.AZURE_DEVOPS
        except Exception:
            return None

    # When provider is known, validate only against that provider
    if expected_provider is not None:
        provider_map = {
            ProviderType.GITHUB: try_github,
            ProviderType.GITLAB: try_gitlab,
            ProviderType.FORGEJO: try_forgejo,
            ProviderType.BITBUCKET: try_bitbucket,
            ProviderType.AZURE_DEVOPS: try_azure_devops,
        }
        if expected_provider in provider_map:
            return await provider_map[expected_provider]()
        return None

    # Try each provider in sequence to detect token type
    if (result := await try_github()) is not None:
        return result
    if (result := await try_gitlab()) is not None:
        return result
    if (result := await try_forgejo()) is not None:
        return result
    if (result := await try_bitbucket()) is not None:
        return result
    if (result := await try_azure_devops()) is not None:
        return result

    return None
