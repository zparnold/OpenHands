"""Callback processor that posts agent review comments to Azure DevOps PRs.

Listens for the first ``MessageEvent`` from the agent in a webhook-triggered
conversation, parses file/line-specific findings from the review text, and posts
them back to the originating Azure DevOps pull request as:

* A **general summary thread** containing the full review text.
* **Inline threads** for each finding that maps to a specific file and line.

The processor disables itself after the first post to avoid duplicate comments.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import UUID

from openhands.app_server.event_callback.event_callback_models import (
    EventCallback,
    EventCallbackProcessor,
    EventCallbackStatus,
)
from openhands.app_server.event_callback.event_callback_result_models import (
    EventCallbackResult,
    EventCallbackResultStatus,
)
from openhands.integrations.service_types import ProviderType
from openhands.sdk import Event, MessageEvent
from openhands.storage.data_models.conversation_metadata import ConversationTrigger

_logger = logging.getLogger(__name__)


@dataclass
class ReviewFinding:
    """A single file/line-specific finding extracted from agent review text."""

    file_path: str
    line: int
    comment: str


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

# Pattern 1: **path/to/file.py:42** or **path/to/file.py:42-50**
_BOLD_FILE_LINE_RE = re.compile(r'\*\*([A-Za-z0-9_./ -]+\.\w+):(\d+)(?:-\d+)?\*\*')

# Pattern 2: `path/to/file.py` line 42  or  `path/to/file.py` (line 42)
_BACKTICK_FILE_LINE_RE = re.compile(
    r'`([A-Za-z0-9_./ -]+\.\w+)`\s*(?:\(?\s*[Ll]ines?\s+(\d+)\s*\)?)'
)

# Pattern 3: path/to/file.py (line 42) — without backticks
_PLAIN_FILE_LINE_RE = re.compile(
    r'(?:^|\s)([A-Za-z0-9_./-]+\.\w+)\s*\(\s*[Ll]ines?\s+(\d+)\s*\)'
)

# Pattern 4: Markdown heading with file path then "Line N" nearby
_HEADING_FILE_RE = re.compile(r'^#{1,4}\s+.*?([A-Za-z0-9_./-]+\.\w+)', re.MULTILINE)
_LINE_NUMBER_RE = re.compile(r'[Ll]ines?\s+(\d+)')


def parse_review_findings(content: str) -> list[ReviewFinding]:
    """Extract file/line-specific findings from agent review text.

    The agent produces free-form markdown. This function applies multiple
    regex patterns to pull out ``(file_path, line_number, comment)`` triples.
    Any content that doesn't match a pattern is silently skipped — those
    portions still appear in the general summary comment posted to the PR.
    """
    findings: list[ReviewFinding] = []
    seen: set[tuple[str, int]] = set()

    # Split content into paragraphs / sections for context extraction
    sections = re.split(r'\n{2,}', content)

    for section in sections:
        matched = False

        # Try bold file:line pattern
        for m in _BOLD_FILE_LINE_RE.finditer(section):
            fp, line_str = m.group(1), m.group(2)
            key = (fp, int(line_str))
            if key not in seen:
                seen.add(key)
                findings.append(
                    ReviewFinding(
                        file_path=fp,
                        line=int(line_str),
                        comment=section.strip(),
                    )
                )
                matched = True

        if matched:
            continue

        # Try backtick file + line pattern
        for m in _BACKTICK_FILE_LINE_RE.finditer(section):
            fp, line_str = m.group(1), m.group(2)
            key = (fp, int(line_str))
            if key not in seen:
                seen.add(key)
                findings.append(
                    ReviewFinding(
                        file_path=fp,
                        line=int(line_str),
                        comment=section.strip(),
                    )
                )
                matched = True

        if matched:
            continue

        # Try plain file (line N) pattern
        for m in _PLAIN_FILE_LINE_RE.finditer(section):
            fp, line_str = m.group(1), m.group(2)
            key = (fp, int(line_str))
            if key not in seen:
                seen.add(key)
                findings.append(
                    ReviewFinding(
                        file_path=fp,
                        line=int(line_str),
                        comment=section.strip(),
                    )
                )
                matched = True

        if matched:
            continue

        # Try heading with file path + nearby line number
        heading_match = _HEADING_FILE_RE.search(section)
        if heading_match:
            fp = heading_match.group(1)
            line_match = _LINE_NUMBER_RE.search(section)
            if line_match:
                line_num = int(line_match.group(1))
                key = (fp, line_num)
                if key not in seen:
                    seen.add(key)
                    findings.append(
                        ReviewFinding(
                            file_path=fp,
                            line=line_num,
                            comment=section.strip(),
                        )
                    )

    return findings


class PostPRReviewCallbackProcessor(EventCallbackProcessor):
    """One-shot callback that posts the agent's review to an Azure DevOps PR."""

    async def __call__(
        self,
        conversation_id: UUID,
        callback: EventCallback,
        event: Event,
    ) -> EventCallbackResult | None:
        if not isinstance(event, MessageEvent):
            return None

        from openhands.app_server.config import (
            get_app_conversation_info_service,
            get_event_callback_service,
        )
        from openhands.app_server.services.injector import InjectorState
        from openhands.app_server.user.specifiy_user_context import (
            ADMIN,
            USER_CONTEXT_ATTR,
        )

        _logger.info(
            'PostPRReviewCallbackProcessor invoked for conversation %s',
            conversation_id,
        )

        state = InjectorState()
        setattr(state, USER_CONTEXT_ATTR, ADMIN)

        try:
            async with (
                get_event_callback_service(state) as event_callback_service,
                get_app_conversation_info_service(
                    state
                ) as app_conversation_info_service,
            ):
                # 1. Look up conversation metadata
                info = await app_conversation_info_service.get_app_conversation_info(
                    conversation_id
                )
                if not info:
                    _logger.warning(
                        'Conversation %s not found, skipping PR review post',
                        conversation_id,
                    )
                    return None

                # 2. Only process Azure DevOps webhook-triggered conversations with a PR
                if info.trigger != ConversationTrigger.AZURE_DEVOPS:
                    _logger.debug(
                        'Conversation %s trigger is %s, not AZURE_DEVOPS — skipping',
                        conversation_id,
                        info.trigger,
                    )
                    # Disable: this processor is irrelevant for non-ADO conversations
                    callback.status = EventCallbackStatus.DISABLED
                    await event_callback_service.save_event_callback(callback)
                    return None

                if not info.pr_number:
                    _logger.debug(
                        'Conversation %s has no PR number — skipping',
                        conversation_id,
                    )
                    callback.status = EventCallbackStatus.DISABLED
                    await event_callback_service.save_event_callback(callback)
                    return None

                pr_number = info.pr_number[0]
                repository = info.selected_repository
                if not repository:
                    _logger.warning(
                        'Conversation %s has no selected_repository — skipping',
                        conversation_id,
                    )
                    callback.status = EventCallbackStatus.DISABLED
                    await event_callback_service.save_event_callback(callback)
                    return None

                # 3. Get the webhook creator's Azure DevOps token
                created_by = info.created_by_user_id
                if not created_by:
                    _logger.warning(
                        'Conversation %s has no created_by_user_id — cannot post review',
                        conversation_id,
                    )
                    callback.status = EventCallbackStatus.DISABLED
                    await event_callback_service.save_event_callback(callback)
                    return None

                from openhands.integrations.provider import ProviderHandler
                from openhands.server.user_auth.user_auth import get_for_user

                user_auth = await get_for_user(created_by)
                provider_tokens = await user_auth.get_provider_tokens()
                if (
                    not provider_tokens
                    or ProviderType.AZURE_DEVOPS not in provider_tokens
                ):
                    _logger.warning(
                        'No Azure DevOps token for user %s — cannot post review',
                        created_by,
                    )
                    callback.status = EventCallbackStatus.DISABLED
                    await event_callback_service.save_event_callback(callback)
                    return None

                from openhands.integrations.azure_devops.azure_devops_service import (
                    AzureDevOpsService,
                )

                handler = ProviderHandler(provider_tokens)
                azure_service: AzureDevOpsService = handler.get_service(
                    ProviderType.AZURE_DEVOPS
                )  # type: ignore[assignment]

                # 4. Post general summary thread
                review_content = (
                    event.content if hasattr(event, 'content') else str(event)
                )
                summary_header = '## OpenHands Code Review\n\n'
                await azure_service.add_pr_thread(
                    repository=repository,
                    pr_number=pr_number,
                    comment_text=summary_header + review_content,
                    status='active',
                )
                _logger.info(
                    'PR_REVIEW_POSTED: summary thread on %s#%s',
                    repository,
                    pr_number,
                )

                # 5. Post inline threads for file-specific findings
                findings = parse_review_findings(review_content)
                inline_count = 0
                for finding in findings:
                    try:
                        await azure_service.add_pr_inline_thread(
                            repository=repository,
                            pr_number=pr_number,
                            comment_text=finding.comment,
                            file_path=finding.file_path,
                            line_start=finding.line,
                        )
                        inline_count += 1
                    except Exception:
                        _logger.warning(
                            'Failed to post inline comment on %s:%d in %s#%d',
                            finding.file_path,
                            finding.line,
                            repository,
                            pr_number,
                            exc_info=True,
                        )

                _logger.info(
                    'PR_REVIEW_POSTED: %d inline threads on %s#%s',
                    inline_count,
                    repository,
                    pr_number,
                )

                # 6. Disable the callback (one-shot)
                callback.status = EventCallbackStatus.DISABLED
                await event_callback_service.save_event_callback(callback)

        except Exception:
            _logger.exception(
                'Error posting PR review for conversation %s', conversation_id
            )
            # Don't re-raise: the conversation should continue even if review posting fails
            return None

        return EventCallbackResult(
            status=EventCallbackResultStatus.SUCCESS,
            event_callback_id=callback.id,
            event_id=event.id,
            conversation_id=conversation_id,
        )
