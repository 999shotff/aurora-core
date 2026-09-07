"""Compute Fabric — provider interface.

Abstract base for CPU, Colab, Lightning providers.
Providers must NOT fabricate availability or GPU info.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import abc
import time

from aurora.ai.synthesis.schemas import ConfidenceLevel
from aurora.compute.schemas import (
    ComputeCapabilities,
    ComputeJob,
    ComputeJobRequest,
    ComputeProviderInfo,
    ComputeProviderStatus,
    ComputeProviderType,
    JobStatus,
)


class ComputeProvider(abc.ABC):
    """Abstract compute provider interface.

    Each provider implements start/stop/health/capabilities/submit/cancel.
    """

    @property
    @abc.abstractmethod
    def provider_type(self) -> ComputeProviderType:
        ...

    @property
    @abc.abstractmethod
    def provider_id(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @abc.abstractmethod
    def start(self) -> None:
        """Start the provider. May be no-op for CPU."""
        ...

    @abc.abstractmethod
    def stop(self) -> None:
        """Stop the provider."""
        ...

    @abc.abstractmethod
    def health(self) -> ComputeProviderStatus:
        """Current health status. Never fabricate READY."""
        ...

    @abc.abstractmethod
    def capabilities(self) -> ComputeCapabilities:
        """What this provider can do."""
        ...

    @abc.abstractmethod
    def submit_job(self, request: ComputeJobRequest) -> ComputeJob:
        """Submit a job. Raises if not ready."""
        ...

    @abc.abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        ...

    def get_info(self) -> ComputeProviderInfo:
        """Get full provider info."""
        return ComputeProviderInfo(
            provider_id=self.provider_id,
            provider_type=self.provider_type,
            name=self.name,
            status=self.health(),
            capabilities=self.capabilities(),
            last_health_check=time.time(),
        )
