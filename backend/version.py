"""
Version management - get version from environment variable (most reliable)
"""
import os
import logging

logger = logging.getLogger(__name__)


def get_version():
    """
    Get application version from environment variable.
    Most reliable method for Docker/production environments.
    Falls back to default version if not set.
    """
    # Get version from environment variable
    version = os.getenv('APP_VERSION') or os.getenv('VERSION')
    
    if version:
        # Remove 'v' prefix if present and strip whitespace
        version = version.strip()
        if version.startswith('v'):
            version = version[1:]
        logger.info(f"Version loaded from environment variable: {version}")
        return version
    
    # Fallback to default
    fallback_version = '2.4.1'
    logger.info(f"Using default version: {fallback_version}")
    return fallback_version

