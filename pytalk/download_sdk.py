"""Download the TeamTalk SDK and extract it to the implementation directory."""

import os

from .tools import ttsdk_downloader


def download_sdk(version: str | None = None, edition: str | None = None) -> None:
    """Download the TeamTalk SDK and extract it to the implementation directory.

    The version and edition can be provided directly or via environment variables:
    - PYTALK_TTSDK_VERSION  (e.g. 'v5.19a' or '5.19a')
    - PYTALK_TTSDK_EDITION  ('standard' | 'pro')
    """
    requested_version = version or os.getenv("PYTALK_TTSDK_VERSION")
    requested_edition = edition or os.getenv("PYTALK_TTSDK_EDITION")
    ttsdk_downloader.install(requested_version, requested_edition)
