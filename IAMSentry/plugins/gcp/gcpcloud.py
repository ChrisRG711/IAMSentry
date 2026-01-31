"""Plugin to read the data from the GCP IAM recommendation API.

This plugin reads IAM recommendations from the GCP Recommender API and yields
records containing the raw recommendation data along with associated insights.

Authentication:
    Supports both Application Default Credentials (recommended) and explicit
    service account key files. For ADC, run: gcloud auth application-default login
"""

import json
from typing import Iterator, List, Optional, Union

from IAMSentry import ioworkers
from IAMSentry.helpers import hlogging

from . import util_gcp

_log = hlogging.get_logger(__name__)


class GCPCloudIAMRecommendations:
    """GCP cloud IAM recommendation plugin with ADC support.

    This plugin reads IAM policy recommendations from the GCP Recommender API.
    It supports both Application Default Credentials (recommended) and explicit
    service account key files.

    Example:
        >>> # Using ADC (recommended)
        >>> reader = GCPCloudIAMRecommendations(projects=['my-project'])
        >>>
        >>> # Using explicit key file
        >>> reader = GCPCloudIAMRecommendations(
        ...     key_file_path='/path/to/key.json',
        ...     projects=['my-project']
        ... )
        >>>
        >>> # Using Secret Manager
        >>> reader = GCPCloudIAMRecommendations(
        ...     key_file_path='gsm://my-project/sa-key',
        ...     projects=['my-project']
        ... )
    """

    def __init__(
        self,
        key_file_path: Optional[str] = None,
        projects: Union[str, List[str]] = "*",
        processes: int = 4,
        threads: int = 10,
        regions: Optional[List[str]] = None,
        **kwargs,
    ):
        """Create an instance of GCPCloudIAMRecommendations plugin.

        Arguments:
            key_file_path: Optional path to service account key file.
                If None, uses Application Default Credentials (ADC).
                Can also be a gsm:// reference to Secret Manager.
            projects: List of project IDs to scan, or '*' for all accessible projects.
            processes: Number of processes to launch (default: 4).
            threads: Number of threads per process (default: 10).
            regions: List of regions to scan (default: ['global']).
            **kwargs: Additional arguments (for plugin compatibility).
        """
        self._key_file_path = key_file_path
        self._projects = projects if isinstance(projects, list) else projects
        self._processes = processes
        self._threads = threads
        self._regions = regions or ["global"]

        # Get credentials and determine authentication method
        try:
            credentials, default_project = util_gcp.get_credentials(key_file_path)
            self._credentials = credentials

            if key_file_path:
                auth_method = "service account key"
            else:
                auth_method = "Application Default Credentials"

            _log.info("Authentication method: %s", auth_method)

        except Exception as e:
            _log.error("Failed to initialize credentials: %s", e)
            raise

        # Scan needs to be done for list of projects or all the projects
        # projects='*' indicates all projects
        if self._projects == "*":
            _log.info("Plugin started in Scan-All-Projects-Mode")
            self._projects = []
            cloudresourcemanager_service = util_gcp.build_resource(
                "cloudresourcemanager", self._key_file_path, "v1"
            )
            for project in util_gcp.get_resource_iterator(
                cloudresourcemanager_service.projects(), "projects"
            ):
                # Only include ACTIVE projects
                if project.get("lifecycleState") == "ACTIVE":
                    self._projects.append(project["projectId"])

        _log.info("Projects to scan: %d", len(self._projects))

        # Get client email for logging
        self._client_email = self._get_client_email()

        _log.info(
            "Initialized; auth: %s; processes: %s; threads: %s; projects: %d",
            "ADC" if not key_file_path else "key_file",
            self._processes,
            self._threads,
            len(self._projects),
        )

    def _get_client_email(self) -> str:
        """Get client email from credentials for logging."""
        # Try to get from key file if provided
        if self._key_file_path and not self._key_file_path.startswith("gsm://"):
            try:
                with open(self._key_file_path) as f:
                    return json.load(f).get("client_email", "<unknown>")
            except Exception:
                pass

        # Try to get from credentials
        if hasattr(self._credentials, "service_account_email"):
            return self._credentials.service_account_email

        return "<ADC user>"

    def read(self):
        """Return a GCP cloud infrastructure configuration record.

        Yields:
            dict: A GCP cloud infrastructure configuration record.

        """
        yield from ioworkers.run(
            self._get_projects, self._get_recommendations, self._processes, self._threads, __name__
        )

    def _get_projects(self):
        """Generate tuples of record types and projects.

        The yielded tuples when unpacked would become arguments for
        :meth:`_get_recommendations`. Each such tuple represents a single unit
        of work that :meth:`_get_recommendations` can work on independently in
        its own worker thread.

        Yields:
            tuple: A tuple which when unpacked forms valid arguments for
                :meth:`_get_recommendations`.

        """
        try:

            for project in self._projects:
                yield ("project_record", "", project, "global")

        except Exception as e:
            _log.error(
                "Failed to fetch projects; key_file_path: %s; " "error: %s: %s",
                self._key_file_path,
                type(e).__name__,
                e,
            )

    def _get_recommendations(self, record_type, project_index, project, zone=None):
        """Generate tuples of record as recommendation for a specific project.

        The yielded tuples when unpacked would become arguments for processor workers

        Yields:
            tuple: A tuple which when unpacked forms valid arguments for
                :meth:`_get_recommendations`.

        """
        _log.info("Fetching recommendations for project : %s ...", hlogging.obfuscated(project))

        parent_string = (
            "projects/{project}/locations/{location}/recommenders/{recommenders}".format(
                project=project, location="global", recommenders="google.iam.policy.Recommender"
            )
        )

        recommendations_service = util_gcp.build_resource("recommender", self._key_file_path, "v1")

        recommendations_iterator = util_gcp.get_resource_iterator(
            (recommendations_service.projects().locations().recommenders().recommendations()),
            "recommendations",
            parent=parent_string,
        )

        for _, recommendation in enumerate(recommendations_iterator):
            recommendation.update({"project": project})

            # Fetch the insights for each recommendation
            _insights = []
            associated_insights = recommendation.get("associatedInsights") or []

            for insight in associated_insights:
                _pattern = insight.get("insight")
                if _pattern:
                    try:
                        i = (
                            recommendations_service.projects()
                            .locations()
                            .insightTypes()
                            .insights()
                            .get(name=_pattern)
                            .execute()
                        )
                        _insights.append(i)
                    except Exception as e:
                        _log.warning(
                            "Failed to fetch insight %s: %s",
                            hlogging.obfuscated(_pattern.split("/")[-1]),
                            e,
                        )

            recommendation.update({"insights": _insights})

            yield {"raw": recommendation}

        _log.info("Fetched recommendations for project: %s", hlogging.obfuscated(project))

    def done(self):
        """Log a message that this plugin is done."""
        _log.info("GCP IAM Audit done")
