"""IAM Risk Score Model.

This module provides the risk scoring algorithm for IAM recommendations.
It calculates two key metrics:

1. **Risk Score**: How risky it is to have the current permissions.
   Higher scores indicate more security risk.

2. **Safe-to-Apply Score**: How safe it is to apply the recommendation.
   Higher scores indicate the recommendation can be safely applied.

Example:
    >>> from IAMSentry.models.iamriskscore import IAMRiskScoreModel
    >>> record = {
    ...     'account_type': 'serviceAccount',
    ...     'account_permission_insights_category': 'REMOVE_ROLE',
    ...     'account_used_permissions': 5,
    ...     'account_total_permissions': 100
    ... }
    >>> model = IAMRiskScoreModel(record)
    >>> scores = model.score()
    >>> print(f"Risk: {scores['risk_score']}, Safe: {scores['safe_to_apply_recommendation_score']}")
"""

from typing import Any, Dict, Optional

from IAMSentry.constants import ACCOUNT_TYPE_WEIGHTS, DEFAULT_SAFE_SCORES
from IAMSentry.helpers import hlogging

_log = hlogging.get_logger(__name__)

__all__ = ["IAMRiskScoreModel"]


class IAMRiskScoreModel:
    """IAM Risk Score Model for GCP IAM Recommendation records.

    This model analyzes IAM recommendations and produces scores that help
    determine the security risk and safety of applying recommendations.

    The scoring algorithm considers:
    - Account type (user, group, serviceAccount)
    - Recommendation type (REMOVE_ROLE, REPLACE_ROLE, etc.)
    - Permission usage patterns (used vs total permissions)

    Attributes:
        _record: The input recommendation record.
        _score: The calculated score dictionary.
    """

    def __init__(self, record: Dict[str, Any]) -> None:
        """Create an instance of IAMRiskScoreModel.

        Arguments:
            record: GCP recommendation record containing:
                - account_type: Type of account (user, group, serviceAccount)
                - account_permission_insights_category: Recommendation category
                - account_used_permissions: Number of permissions actually used
                - account_total_permissions: Total permissions granted
        """
        self._record = record
        self._score: Dict[str, Any] = {
            "safe_to_apply_recommendation_score": None,
            "safe_to_apply_recommendation_score_factors": None,
            "risk_score": None,
            "risk_score_factors": None,
            "over_privilege_score": None,
        }

    def score(self) -> Dict[str, Any]:
        """Calculate and return risk scores for the recommendation.

        The scoring algorithm uses the following logic:

        **Safe-to-Apply Score** (higher = safer to apply):
        - Base score depends on account type:
          - user: 60 (users can re-request access easily)
          - group: 30 (groups have broader impact)
          - serviceAccount: 0 (highest risk to modify)
        - Bonus for recommendation type:
          - REMOVE_ROLE: +30 (complete removal is clearer)
          - REPLACE_ROLE: +20 (replacement maintains some access)
          - Other: +10
        - Adjusted by usage ratio (more unused = safer to remove)

        **Risk Score** (higher = more risky to keep current state):
        - Based on excess permission ratio
        - Weighted by account type (serviceAccounts weighted highest)
        - Formula: (excess_ratio ^ weight) * 100

        Returns:
            Dictionary containing:
                - safe_to_apply_recommendation_score: 0-100 safety score
                - safe_to_apply_recommendation_score_factors: Number of factors used
                - risk_score: 0-100 risk score
                - risk_score_factors: Number of factors used
                - over_privilege_score: Percentage of unused permissions
        """
        account_type = self._record.get("account_type", "unknown")
        suggestion_type = self._record.get("account_permission_insights_category", "")
        used_permissions = int(self._record.get("account_used_permissions", 0))

        # Handle None or missing total permissions
        total_permissions_raw = self._record.get("account_total_permissions")
        if total_permissions_raw is None or total_permissions_raw == "":
            total_permissions = max(used_permissions + 1, 1)
        else:
            total_permissions = max(int(total_permissions_raw), 1)

        # Calculate excess permissions
        excess_permissions = max(total_permissions - used_permissions, 0)

        # Ensure we don't divide by zero
        if total_permissions < 1:
            total_permissions = 1

        excess_ratio = excess_permissions / total_permissions

        # --- Calculate Safe-to-Apply Score ---
        safe_score = self._calculate_safe_to_apply_score(
            account_type, suggestion_type, excess_ratio
        )

        self._score.update(
            {
                "safe_to_apply_recommendation_score": safe_score,
                "safe_to_apply_recommendation_score_factors": 3,
            }
        )

        # --- Calculate Risk Score ---
        risk_score = self._calculate_risk_score(account_type, excess_ratio)

        self._score.update({"risk_score": risk_score, "risk_score_factors": 2})

        # --- Calculate Over-Privilege Score ---
        over_privilege_score = round(excess_ratio * 100)

        self._score.update({"over_privilege_score": over_privilege_score})

        return self._score

    def _calculate_safe_to_apply_score(
        self, account_type: str, suggestion_type: str, excess_ratio: float
    ) -> int:
        """Calculate how safe it is to apply the recommendation.

        Arguments:
            account_type: Type of account (user, group, serviceAccount).
            suggestion_type: Type of recommendation.
            excess_ratio: Ratio of unused to total permissions.

        Returns:
            Safety score from 0-100 (higher = safer).
        """
        # Base score by account type
        # Users can easily request access again, groups have broader impact,
        # service accounts are most critical
        base_scores = {
            "user": 60,
            "group": 30,
            "serviceAccount": 0,
        }
        safe_score = base_scores.get(account_type, 0)

        # Bonus by suggestion type
        # REMOVE_ROLE is clearer (complete removal), REPLACE_ROLE maintains some access
        if suggestion_type == "REMOVE_ROLE":
            safe_score += 30
        elif suggestion_type == "REPLACE_ROLE":
            safe_score += 20
        else:
            safe_score += 10

        # Adjust by excess ratio - more unused permissions = safer to remove
        # If excess_ratio is high (e.g., 0.9), we divide by a small number, increasing score
        # If excess_ratio is low (e.g., 0.1), we divide by a larger number, decreasing score
        if excess_ratio > 0:
            # Scale factor: higher excess = higher multiplier (up to 2x)
            multiplier = 1 + excess_ratio
            safe_score = int(safe_score * multiplier)
        else:
            # No excess permissions - not safe to remove
            safe_score = max(safe_score // 2, 0)

        # Cap at 100
        return min(round(safe_score), 100)

    def _calculate_risk_score(self, account_type: str, excess_ratio: float) -> int:
        """Calculate the security risk of keeping current permissions.

        Higher excess permissions = higher risk, especially for service accounts.

        Arguments:
            account_type: Type of account (user, group, serviceAccount).
            excess_ratio: Ratio of unused to total permissions.

        Returns:
            Risk score from 0-100 (higher = more risky).
        """
        # Weight by account type - service accounts are highest risk
        # because they often have automated access and can be exploited
        weights = ACCOUNT_TYPE_WEIGHTS.copy()
        weight = weights.get(account_type, 2)

        # Risk formula: excess_ratio * weight * 100
        # This gives higher risk for:
        # - Higher excess ratio (more unused permissions)
        # - Higher weight accounts (serviceAccount > group > user)
        #
        # We use a linear formula here instead of exponential because:
        # - It's more predictable and interpretable
        # - 50% excess permissions should give meaningful risk scores
        risk_score = excess_ratio * weight * 20  # Scale to get good distribution

        # Ensure we cap at 100
        return min(round(risk_score), 100)
