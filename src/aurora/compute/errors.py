"""Compute Fabric — domain errors.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations


class ComputeError(Exception):
    """Base compute error."""


class ProviderNotConfigured(ComputeError):
    """Provider credentials or endpoint not configured."""


class ProviderUnavailable(ComputeError):
    """Provider is configured but not reachable or not ready."""


class ProviderBusy(ComputeError):
    """Provider is at capacity."""


class JobTimeout(ComputeError):
    """Job exceeded timeout."""


class JobNotFound(ComputeError):
    """Job ID not found."""


class UnauthorizedWorker(ComputeError):
    """Worker authentication failed."""


class DuplicateWorker(ComputeError):
    """Worker already registered."""


class WorkerNotFound(ComputeError):
    """Worker ID not found."""


class InvalidMode(ComputeError):
    """Invalid compute mode."""


class InvalidProvider(ComputeError):
    """Invalid provider type."""


class FallbackRequired(ComputeError):
    """Explicit provider unavailable, fallback required."""
