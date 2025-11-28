"""Script for downloading and installing the TeamTalk SDK."""

#!/usr/bin/env python3

# Modified from https://github.com/gumerov-amir/TTMediaBot

import platform
import shutil
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set

import bs4
import patoolib
import requests

from . import downloader

url = "https://bearware.dk/teamtalksdk"

cd = Path(__file__).parent.parent.resolve()
HEADERS = {
    "user-agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
    ),
}
DEFAULT_EDITION = "standard"


def get_url_suffix_from_platform() -> str:
    """Determine the correct URL suffix for the SDK.

    This is based on the current platform and architecture.
    """
    machine = platform.machine()
    if sys.platform == "win32":
        architecture = platform.architecture()
        if machine in {"AMD64", "x86"}:
            if architecture[0] == "64bit":
                return "win64"
            return "win32"
        sys.exit("Native Windows on ARM is not supported")
    elif sys.platform == "darwin":
        sys.exit("Darwin is not supported")
    elif machine in {"AMD64", "x86_64"}:
        return "ubuntu22_x86_64"
    elif "arm" in machine:
        return "raspbian_armhf"
    else:
        sys.exit("Your architecture is not supported")


def _extract_versions(page: bs4.BeautifulSoup) -> List[str]:
    """Return the list of version directory names (e.g. 'v5.19a') ordered as on the page."""
    found: Set[str] = set()
    ordered: List[str] = []
    for anchor in page.select("li > a"):
        href = anchor.get("href", "").rstrip("/")
        if href.startswith("v") and len(href) > 1:
            if href not in found:
                found.add(href)
                ordered.append(href)
    return ordered


def _normalize_version(requested: Optional[str], available: Iterable[str]) -> str:
    versions = list(available)
    if not versions:
        sys.exit("No TeamTalk SDK versions found on bearware.dk")
    if requested is None:
        return versions[0]
    candidate = requested if requested.startswith("v") else f"v{requested}"
    if candidate in versions:
        return candidate
    sys.exit(f"Version '{requested}' not available. Found: {', '.join(versions)}")


def _normalize_edition(edition: Optional[str]) -> str:
    if edition is None:
        return DEFAULT_EDITION
    normalized = edition.lower()
    if normalized in {"standard", "std", "community"}:
        return "standard"
    if normalized in {"professional", "pro"}:
        return "pro"
    sys.exit("Edition must be 'standard' or 'pro'")


def download(version: Optional[str] = None, edition: Optional[str] = None) -> None:
    """Download the TeamTalk SDK (Standard or Professional) from the official website."""
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    page = bs4.BeautifulSoup(r.text, features="html.parser")
    chosen_version = _normalize_version(version, _extract_versions(page))
    chosen_edition = _normalize_edition(edition)
    suffix = get_url_suffix_from_platform()
    prefix = "tt5prosdk" if chosen_edition == "pro" else "tt5sdk"
    download_url = f"{url}/{chosen_version}/{prefix}_{chosen_version}_{suffix}.7z"
    print(f"Downloading {chosen_edition} edition from {download_url}")
    downloader.download_file(download_url, str(cd / "ttsdk.7z"))


def extract() -> None:
    """Extract the downloaded TeamTalk SDK archive."""
    try:
        (cd / "ttsdk").mkdir()
    except FileExistsError:
        shutil.rmtree(cd / "ttsdk")
        (cd / "ttsdk").mkdir()
    patoolib.extract_archive(str(cd / "ttsdk.7z"), outdir=str(cd / "ttsdk"))


def move(edition: str = DEFAULT_EDITION) -> None:
    """Move the extracted SDK files to their final destination."""
    path = cd / "ttsdk" / next((cd / "ttsdk").iterdir())
    libraries = ["TeamTalk_DLL", "TeamTalkPy"]
    try:
        (cd / "implementation").mkdir(parents=True)
    except FileExistsError:
        shutil.rmtree(cd / "implementation")
        (cd / "implementation").mkdir(parents=True)
    for library in libraries:
        try:
            (path / "Library" / library).rename(cd / "implementation" / library)
        except OSError:
            shutil.rmtree(cd / "implementation" / library)
            (path / "Library" / library).rename(cd / "implementation" / library)
        try:
            (cd / "implementation" / "__init__.py").unlink()
        except OSError:
            pass
        finally:
            with (cd / "implementation" / "__init__.py").open("w") as f:
                f.write("")
    # Pro edition ships libraries named *Pro; duplicate to legacy names expected by TeamTalkPy.
    if edition == "pro":
        dll_dir = cd / "implementation" / "TeamTalk_DLL"
        copies = [
            ("TeamTalk5Pro.dll", "TeamTalk5.dll"),
            ("libTeamTalk5Pro.so", "libTeamTalk5.so"),
            ("libTeamTalk5Pro.dylib", "libTeamTalk5.dylib"),
        ]
        for src, dst in copies:
            src_path = dll_dir / src
            dst_path = dll_dir / dst
            if src_path.exists() and not dst_path.exists():
                shutil.copy2(src_path, dst_path)


def clean() -> None:
    """Clean up downloaded and extracted SDK files."""
    (cd / "ttsdk.7z").unlink()
    shutil.rmtree(cd / "ttsdk")
    shutil.rmtree(cd / "implementation" / "TeamTalkPy" / "test")


def install(version: Optional[str] = None, edition: Optional[str] = None) -> None:
    """Install the TeamTalk SDK components."""
    print("Installing TeamTalk sdk components")
    try:
        print("Downloading latest sdk version")
        download(version, edition)
    except requests.exceptions.RequestException as e:
        print("Failed to download sdk. Error: ", e)
        sys.exit(1)
    try:
        print("Downloaded. extracting")
        extract()
    except patoolib.util.PatoolError as e:
        print("Failed to extract sdk. Error: ", e)
        print(
            "This can typically happen, if you do not have 7zip or equivalent "
            "installed on your system."
        )
        print(
            "On debian based systems, you can install 7zip by running "
            "'sudo apt install p7zip'"
        )
        print("On Windows, you need to have 7zip installed and added to your PATH")
        sys.exit(1)
    print("Extracted. moving")
    move(_normalize_edition(edition))
    if not (cd / "implementation" / "TeamTalk_DLL").exists():
        print("Failed to move TeamTalk_DLL")
        sys.exit(1)
    if not (cd / "implementation" / "TeamTalkPy").exists():
        print("Failed to move TeamTalkPy")
        sys.exit(1)
    print("moved. cleaning")
    clean()
    print("cleaned.")
    print("Installed")
