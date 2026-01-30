"""Base classes and common utilities for GCP plugins.

This module provides shared functionality for GCP IAM plugins to reduce
code duplication and ensure consistent behavior across plugins.
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, List, Optional, Set

from IAMSentry.helpers import hlogging
from . import util_gcp

_log = hlogging.get_logger(__name__)


class GCPPluginBase(ABC):
    """Abstract base class for GCP plugins.

    Provides common functionality for authentication, resource management,
    and statistics tracking used by all GCP plugins.

    Attributes:
        _key_file_path: Optional path to service account key file.
        _credentials: GCP credentials object.
        _stats: Dictionary tracking plugin statistics.
    """

    def __init__(
        self,
        key_file_path: Optional[str] = None,
        **kwargs
    ):
        """Initialize GCP plugin base.

        Arguments:
            key_file_path: Optional path to service account key file.
                If None, uses Application Default Credentials (ADC).
            **kwargs: Additional arguments passed to subclasses.
        """
        self._key_file_path = key_file_path
        self._credentials = None
        self._project_id = None
        self._stats: Dict[str, int] = {}

        # Initialize credentials
        self._init_credentials()

    def _init_credentials(self) -> None:
        """Initialize GCP credentials."""
        try:
            self._credentials, self._project_id = util_gcp.get_credentials(
                self._key_file_path
            )
            _log.debug(
                'Initialized credentials (project: %s, key_file: %s)',
                self._project_id,
                'ADC' if not self._key_file_path else self._key_file_path
            )
        except Exception as e:
            _log.error('Failed to initialize credentials: %s', e)
            raise

    def _build_service(
        self,
        service_name: str,
        version: str = 'v1'
    ) -> Any:
        """Build a GCP API service resource.

        Arguments:
            service_name: Name of the GCP service (e.g., 'cloudresourcemanager').
            version: API version (default: 'v1').

        Returns:
            googleapiclient.discovery.Resource for API interactions.
        """
        return util_gcp.build_resource(
            service_name,
            self._key_file_path,
            version
        )

    def _increment_stat(self, stat_name: str, amount: int = 1) -> None:
        """Increment a statistics counter.

        Arguments:
            stat_name: Name of the statistic to increment.
            amount: Amount to increment by (default: 1).
        """
        self._stats[stat_name] = self._stats.get(stat_name, 0) + amount

    def get_stats(self) -> Dict[str, int]:
        """Get current statistics.

        Returns:
            Dictionary of statistic names to values.
        """
        return self._stats.copy()

    @abstractmethod
    def done(self) -> None:
        """Perform cleanup and log completion.

        Subclasses should implement this to log statistics and
        perform any necessary cleanup.
        """
        pass


class ValidationMixin:
    """Mixin providing common validation functionality for IAM plugins.

    Provides blocklist, allowlist, and safety score validation
    that can be shared across different processor plugins.
    """

    def init_validation_config(
        self,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize validation configuration.

        Arguments:
            config: Configuration dictionary containing validation settings.
        """
        config = config or {}

        # Blocklist settings
        self._blocklist_projects: Set[str] = set(
            config.get('blocklist_projects', [])
        )
        self._blocklist_accounts: Set[str] = set(
            config.get('blocklist_accounts', [])
        )
        self._blocklist_account_types: Set[str] = set(
            config.get('blocklist_account_types', ['serviceAccount'])
        )

        # Allowlist settings
        self._allowlist_projects: Optional[Set[str]] = None
        if 'allowlist_projects' in config:
            self._allowlist_projects = set(config['allowlist_projects'])
        self._allowlist_account_types: Set[str] = set(
            config.get('allowlist_account_types', ['user', 'group'])
        )

        # Safety score thresholds by account type
        self._min_safe_scores: Dict[str, int] = {
            'user': config.get('min_safe_to_apply_score_user', 60),
            'group': config.get('min_safe_to_apply_score_group', 60),
            'serviceaccount': config.get('min_safe_to_apply_score_SA', 60),
        }

        # Critical account patterns that require extra review
        self._critical_patterns: List[str] = config.get(
            'critical_account_patterns',
            ['prod', 'admin', 'terraform', 'deployment', 'cicd', 'github']
        )

        _log.debug(
            'Validation config initialized: blocklist_projects=%d, '
            'blocklist_accounts=%d, allowlist_account_types=%s',
            len(self._blocklist_projects),
            len(self._blocklist_accounts),
            self._allowlist_account_types
        )

    def validate_blocklist(
        self,
        project: str,
        account_id: str,
        account_type: str
    ) -> bool:
        """Check if an account passes blocklist validation.

        Arguments:
            project: GCP project ID.
            account_id: Account identifier (email).
            account_type: Type of account (user, group, serviceAccount).

        Returns:
            True if the account is NOT blocked, False if blocked.
        """
        if project in self._blocklist_projects:
            _log.debug(
                'Project %s is in blocklist',
                hlogging.obfuscated(project)
            )
            return False

        if account_id in self._blocklist_accounts:
            _log.debug(
                'Account %s is in blocklist',
                hlogging.obfuscated(account_id)
            )
            return False

        if account_type in self._blocklist_account_types:
            _log.debug('Account type %s is in blocklist', account_type)
            return False

        return True

    def validate_allowlist(
        self,
        project: Optional[str] = None,
        account_type: Optional[str] = None
    ) -> bool:
        """Check if an account passes allowlist validation.

        Arguments:
            project: Optional GCP project ID.
            account_type: Optional account type.

        Returns:
            True if the account is allowed, False otherwise.
        """
        # Check project allowlist if configured
        if self._allowlist_projects is not None and project:
            if project not in self._allowlist_projects:
                _log.debug(
                    'Project %s not in allowlist',
                    hlogging.obfuscated(project)
                )
                return False

        # Check account type allowlist
        if account_type and account_type not in self._allowlist_account_types:
            _log.debug('Account type %s not in allowlist', account_type)
            return False

        return True

    def validate_safety_score(
        self,
        account_type: str,
        safety_score: int
    ) -> bool:
        """Check if the safety score meets minimum threshold.

        Arguments:
            account_type: Type of account.
            safety_score: Calculated safety score.

        Returns:
            True if the score meets the threshold, False otherwise.
        """
        account_type_lower = account_type.lower()
        min_score = self._min_safe_scores.get(account_type_lower, 60)

        if safety_score >= min_score:
            _log.debug(
                'Safety score %d >= minimum %d for account type %s',
                safety_score, min_score, account_type
            )
            return True

        _log.debug(
            'Safety score %d < minimum %d for account type %s',
            safety_score, min_score, account_type
        )
        return False

    def is_critical_account(self, account_id: str) -> bool:
        """Check if an account matches critical patterns.

        Arguments:
            account_id: Account identifier to check.

        Returns:
            True if the account matches any critical pattern.
        """
        account_lower = account_id.lower()
        for pattern in self._critical_patterns:
            if pattern in account_lower:
                _log.debug(
                    'Account %s matches critical pattern: %s',
                    hlogging.obfuscated(account_id), pattern
                )
                return True
        return False


class IAMPolicyModifier:
    """Utility class for modifying GCP IAM policies.

    Provides safe methods for adding and removing IAM policy bindings.
    All modifications are performed on copies of the policy to prevent
    accidental mutations.
    """

    @staticmethod
    def remove_member(
        policy: Dict[str, Any],
        role: str,
        member: str
    ) -> Dict[str, Any]:
        """Remove a member from a role binding.

        Arguments:
            policy: IAM policy dictionary.
            role: Role to remove member from.
            member: Member identifier to remove.

        Returns:
            Updated policy dictionary.
        """
        # Work on a copy to prevent accidental mutations
        updated_policy = json.loads(json.dumps(policy))

        for binding in updated_policy.get('bindings', []):
            if binding.get('role') == role:
                members = binding.get('members', [])
                if member in members:
                    members.remove(member)
                    _log.debug(
                        'Removed member %s from role %s',
                        hlogging.obfuscated(member), role
                    )
                    # Remove empty bindings
                    if not members:
                        updated_policy['bindings'].remove(binding)
                break

        return updated_policy

    @staticmethod
    def add_member(
        policy: Dict[str, Any],
        role: str,
        member: str
    ) -> Dict[str, Any]:
        """Add a member to a role binding.

        Arguments:
            policy: IAM policy dictionary.
            role: Role to add member to.
            member: Member identifier to add.

        Returns:
            Updated policy dictionary.
        """
        # Work on a copy to prevent accidental mutations
        updated_policy = json.loads(json.dumps(policy))

        # Look for existing binding for this role
        for binding in updated_policy.get('bindings', []):
            if binding.get('role') == role:
                members = binding.get('members', [])
                if member not in members:
                    members.append(member)
                    _log.debug(
                        'Added member %s to existing role %s',
                        hlogging.obfuscated(member), role
                    )
                return updated_policy

        # No existing binding, create new one
        if 'bindings' not in updated_policy:
            updated_policy['bindings'] = []

        updated_policy['bindings'].append({
            'role': role,
            'members': [member]
        })
        _log.debug(
            'Added member %s to new role binding %s',
            hlogging.obfuscated(member), role
        )

        return updated_policy

    @staticmethod
    def replace_role(
        policy: Dict[str, Any],
        member: str,
        old_role: str,
        new_role: str
    ) -> Dict[str, Any]:
        """Replace a role for a member (remove old, add new).

        Arguments:
            policy: IAM policy dictionary.
            member: Member identifier.
            old_role: Role to remove.
            new_role: Role to add.

        Returns:
            Updated policy dictionary.
        """
        updated_policy = IAMPolicyModifier.remove_member(policy, old_role, member)
        updated_policy = IAMPolicyModifier.add_member(updated_policy, new_role, member)

        _log.debug(
            'Replaced role for %s: %s -> %s',
            hlogging.obfuscated(member), old_role, new_role
        )

        return updated_policy

    @staticmethod
    def get_member_roles(
        policy: Dict[str, Any],
        member: str
    ) -> List[str]:
        """Get all roles assigned to a member.

        Arguments:
            policy: IAM policy dictionary.
            member: Member identifier.

        Returns:
            List of role names assigned to the member.
        """
        roles = []
        for binding in policy.get('bindings', []):
            if member in binding.get('members', []):
                roles.append(binding.get('role'))
        return roles
