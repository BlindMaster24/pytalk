# Gemini Context: Pytalk Project

## ❗ Agent's Core Principle
> **1. Focus on User Intent:** The AI agent's primary goal is to assist the user effectively. This requires careful analysis of user requests to ensure the agent's actions align with the user's specific intent, even if it requires deviation from a standard documented workflow.
>
> **2. Proactive Research and Problem-Solving:** The agent is expected to be a proactive problem-solver. When faced with questions, errors, or tasks that require knowledge not present in the immediate context (e.g., unfamiliar library usage, new API documentation, troubleshooting obscure errors), the agent must utilize its available tools and protocols. This includes performing web searches to consult official documentation and forums, as well as leveraging standards like **MCP (Model Context Protocol)** where applicable to interact with tools and gather context. The goal is to resolve ambiguities and acquire necessary knowledge independently.
>
> **3. Tool Preference and Persistence for File Manipulation:** When modifying file content or creating/deleting temporary files, the agent must prioritize the use of dedicated file manipulation tools (`write_file`, `replace`). If an operation with these tools initially fails, the agent should make a maximal effort to resolve the issue and succeed with the preferred tools. Only if these tools prove insufficient after exhaustive attempts, and *only upon explicit user request*, should alternative methods (e.g., shell commands like `echo`, `rm`, `del`) be considered for file operations.

---

## 1. Project Overview

**Pytalk** is a Python library designed to simplify the creation of bots for the TeamTalk 5 Conferencing System. It provides a high-level, asynchronous, event-driven API that wraps the underlying TeamTalk 5 SDK, abstracting away much of the low-level complexity.

**Key Technologies Used:**
-   **Python 3.11+**: Primary development language.
-   **`asyncio`**: For asynchronous and event-driven programming.
-   **`hatch`**: For project management, build, and task running.
-   **`pre-commit`**: For managing Git hooks and ensuring code quality.
-   **`ruff`**: Code formatter and linter.
-   **`Sphinx`**: For documentation generation.
-   **`gh` (GitHub CLI)**: For interacting with GitHub (e.g., managing Pull Requests, checking CI status).

The library's architecture is centered around two main classes:
-   `TeamTalkBot`: The primary entry point for creating a bot. It manages the asyncio event loop, dispatches events, and holds multiple server connections.
-   `TeamTalkInstance`: Represents a single connection to a TeamTalk server. It handles all direct communication with the SDK, event processing, and actions related to that specific server.

The project is built for Python 3.11+ and relies heavily on `asyncio` for its asynchronous operations.

## 2. Project Structure

-   `.github/workflows/`: Contains GitHub Actions workflows for Continuous Integration (CI).
-   `docs/`: Contains all files related to the Sphinx documentation.
-   `for_gemini/`: A dedicated directory for user-provided files for the Gemini agent. This directory is ignored by Git.
-   `pytalk/`: The main source code for the library.
    -   `implementation/`: Houses the pre-compiled TeamTalk 5 SDK files. This directory is populated automatically by a download script.
    -   `tools/`: Contains helper scripts, primarily for downloading the SDK.
-   **Root Directory**: Contains project configuration files (`pyproject.toml`, `.pre-commit-config.yaml`, etc.), the main README, and license information.

## 3. Commit Message Conventions

To maintain a clear, readable, and automated commit history, this project adheres to the following conventions for all Git commits.

-   **Language**: All commit messages must be written in English.
-   **Structure**: Commits must follow the **Conventional Commits** specification.
-   **Emoji Prefix**: Each commit message should be prefixed with a relevant **Gitmoji** icon.

### Conventional Commits

This is a specification for adding human and machine-readable meaning to commit messages. It provides a simple set of rules for creating an explicit commit history, which makes it easier to write automated tools on top of. The commit message should be structured as follows:

```
<gitmoji> <type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

-   **type**: Must be one of the following: `feat` (new feature), `fix` (bug fix), `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`.
-   **scope**: An optional noun describing a section of the codebase (e.g., `instance`, `docs`, `ci`).
-   **subject**: A concise description of the change.

**Reference**: [Conventional Commits Specification](https://www.conventionalcommits.org/)

### Gitmoji

Gitmoji is an emoji guide for commit messages, making them easier to identify and browse. The chosen emoji should correspond to the type and content of the commit.

**Example Commit Messages:**
-   `✨ feat(auth): implement user registration endpoint`
-   `🐛 fix(streamer): prevent crash on empty audio data`
-   `📚 docs(api): add documentation for the new `Server` class`

**Reference**: [Gitmoji Website & Emoji List](https://gitmoji.dev/)

## 4. File-by-File Breakdown

### 4.1. Configuration & Metadata

-   **`.gitignore`**: A standard Python gitignore file. It excludes common files like `__pycache__`, virtual environments (`.venv`), build artifacts (`dist/`, `build/`), and test reports. It also specifically ignores the downloaded SDK files (`pytalk/implementation/TeamTalk*`) and the `/for_gemini/` directory.
-   **`.pre-commit-config.yaml`**: Configures pre-commit hooks to ensure code quality before commits. It uses:
    -   `pre-commit-hooks`: For basic checks like trailing whitespace, file endings, and syntax validation (YAML, TOML, AST).
    -   `ruff`: For consistent code formatting and linting.
    -   `hatch run dev:typecheck`: For type checking with `mypy`.
-   **`.python-version`**: Specifies that the project uses Python `3.11`. This is likely used by tools like `pyenv`.
-   **`.readthedocs.yaml`**: Configuration for building the documentation on Read the Docs. It defines the build environment (Ubuntu 22.04), system dependencies (`libpulse0`, `p7zip-full`), Python version (3.11), and the steps to install project dependencies using `hatch` before building the Sphinx documentation.
-   **`pyproject.toml`**: The primary project definition file, now managed by `hatch`.
    -   `[project]`: Defines metadata like the package name (`py-talk-ex`), version, dependencies (`beautifulsoup4`, `patool`, `requests`), and supported Python version (`>=3.11`).
    -   `[tool.hatch.envs.<env-name>]`: Defines development and documentation environments, including their dependencies and scripts.
    -   `[tool.ruff]` & `[tool.mypy]`: Configures the behavior of the Ruff formatter/linter and Mypy type checker.
-   **`tea.yaml`**: A configuration file for `tea.xyz`, a universal package manager. It specifies the code owners for the project.

### 4.1.1. Versioning with `versioningit` Best Practices

The project utilizes `versioningit` for dynamic versioning based on Git tags. To ensure correct versioning, especially for PyPI publications, adhere to the following best practices:

-   **Annotated Tags are Preferred:** `versioningit` primarily considers annotated Git tags for version calculation. While lightweight tags can be configured, using annotated tags (`git tag -a <version> -m "Release <version>"`) is the recommended and default behavior.
-   **Avoid `write` Configuration for PyPI Releases:** The `[tool.versioningit.write]` subtable, if configured, modifies files in the working tree. This causes `versioningit` to consider the repository "dirty," leading to versions with local identifiers (e.g., `+dYYYYMMDD`), which are rejected by PyPI. For PyPI-compliant releases, rely on the `onbuild` hook (configured under `[tool.hatch.build.hooks.versioningit-onbuild]`) to inject the version during the build process without altering the Git working tree.
-   **Ensure Full Git History in CI:** In Continuous Integration (CI) environments (e.g., GitHub Actions), it is crucial to fetch the full Git history. This is achieved by setting `fetch-depth: 0` in the `actions/checkout@v4` step. Without full history, `versioningit` cannot accurately determine the version from Git tags.
-   **`[tool.versioningit.format]` for Clean Versions:** The `[tool.versioningit.format]` section in `pyproject.toml` should be configured to ensure that when the repository is in an "exact" (tagged) state, the version is formatted without any local identifiers. For example, `clean = "{base_version}"` ensures that a tagged commit results in a clean version number.


### 4.2. Core Library (`pytalk/`)

-   **`__init__.py`**: The main entry point of the `pytalk` package. Its primary role is to ensure the TeamTalk SDK is available. It attempts to import the SDK, and if it fails (i.e., the SDK hasn't been downloaded), it calls `download_sdk.py` to fetch and install it. It also exposes the main classes (`TeamTalkBot`, `Channel`, `User`, etc.) for easy import.
-   **`bot.py`**: Defines the `TeamTalkBot` class, the main user-facing class. It manages the asyncio event loop, holds a list of `TeamTalkInstance` objects (one for each server connection), and contains the event dispatching system (`@bot.event` decorator).
-   **`instance.py`**: Defines the `TeamTalkInstance` class, which is the heart of the library. This class inherits from the raw `TeamTalk5` SDK class and wraps its functionality. It handles connecting, logging in, processing the event queue (`_process_events`), sending commands, managing user/channel objects, and implementing features like automatic reconnection with backoff.
-   **`_utils.py`**: A collection of internal helper functions. This includes functions for waiting for specific SDK events (`_waitForEvent`), converting between volume percentages and internal SDK values (`percent_to_ref_volume`), and dynamically getting/setting attributes on SDK objects (`_get_tt_obj_attribute`).
-   **`audio.py`**: Defines wrapper classes (`AudioBlock`, `MuxedAudioBlock`) for audio data received from the server. It also defines the CTypes function factories (`_AcquireUserAudioBlock`, `_ReleaseUserAudioBlock`) for safe interaction with the SDK's audio buffer.
-   **`backoff.py`**: Implements the `Backoff` class, which provides an exponential backoff strategy with jitter. This is used by `TeamTalkInstance` to handle connection retries without overwhelming the server.
-   **`channel.py`**: Defines the `Channel` class, a high-level wrapper around the SDK's channel object. It provides methods for sending messages to the channel, getting users/files, and managing channel properties.
-   **`codec.py`**: Defines the `CodecType` helper class, which allows accessing SDK media codec identifiers (e.g., `CodecType.WEBM_VP8`) using user-friendly names.
-   **`device.py`**: Defines the `SoundDevice` class, a wrapper for the SDK's `SoundDevice` struct, making it easier to inspect available audio devices.
-   **`enums.py`**: Contains Pythonic enumerations and helper classes for various TeamTalk concepts, such as `TeamTalkServerInfo` (a dataclass for server connection details), `UserStatusMode`, and the `Status` helper for building complex user statuses.
-   **`exceptions.py`**: Defines custom exceptions for the library, like `TeamTalkException` (the base exception) and `PermissionError`.
-   **`message.py`**: Defines classes for different message types (`ChannelMessage`, `DirectMessage`, `BroadcastMessage`). They inherit from a base `Message` class and provide context-aware `reply()` methods.
-   **`permission.py`**: Defines the `Permission` helper class (using a metaclass) to provide easy, attribute-style access to the SDK's user permission flags (e.g., `Permission.KICK_USERS`).
-   **`server.py`**: Defines the `Server` class, which represents the server itself and provides methods for server-wide actions like getting all users/channels, managing server properties, and sending broadcast messages.
-   **`statistics.py`**: Defines the `Statistics` class, a wrapper for the server statistics object provided by the SDK.
-   **`streamer.py`**: Contains the `Streamer` class for streaming audio to a channel. It uses `ffmpeg` and `yt-dlp` (if available) to process local files and URLs into a raw PCM audio stream that can be fed into the TeamTalk SDK.
-   **`subscription.py`**: Defines the `Subscription` helper class, similar to `Permission`, for accessing user subscription flags (e.g., `Subscription.USER_TEXTMESSAGE`).
-   **`tt_file.py`**: Defines the `RemoteFile` class, a wrapper for file objects on the server.
-   **`user.py`**: Defines the `User` class, a wrapper for a connected user, providing methods to send direct messages, kick, ban, etc.
-   **`user_account.py`**: Defines `UserAccount` and `BannedUserAccount` classes, which represent stored user accounts on the server (as opposed to currently connected users).

### 4.3. SDK Downloader (`pytalk/tools/`)

-   **`downloader.py`**: A simple utility with a `download_file` function that uses the `requests` library to download a file from a URL.
-   **`ttsdk_downloader.py`**: The main script responsible for fetching the TeamTalk SDK. It scrapes the BearWare.dk website to find the correct SDK version (`5.15`), downloads the 7z archive for the appropriate OS and architecture, extracts it using `patoolib`, and moves the necessary `TeamTalk_DLL` and `TeamTalkPy` folders into the `pytalk/implementation/` directory.

### 4.4. Documentation (`docs/`)

-   **`conf.py`**: The main Sphinx configuration file. It sets up the project version, extensions (`napoleon`, `autodoc`, etc.), HTML theme (`scrolls`), and other settings.
-   **`index.rst`**: The main landing page for the documentation.
-   **`api.rst`**: Uses `autodoc` directives to generate the API reference from the docstrings in the source code.
-   **`events.rst`**: Documents the available events using `csv-table` directives, which pull data from the `.csv` files in `_static/csv/`.
-   **`whats-new.rst`**: The project's changelog.
-   **`make.bat` & `Makefile`**: Build scripts for Sphinx on Windows and Unix-like systems, respectively.

### 4.5. Continuous Integration (`.github/workflows/`)

-   **`ci.yaml`**: Defines the GitHub Actions CI pipeline.
    -   **`test` job**: Runs on every push and pull request across multiple operating systems (Ubuntu, Windows) and Python versions (3.9-3.13). It installs dependencies with `hatch`, downloads the SDK, and runs `pre-commit`.
    -   **`builder_pytalk` job**: After tests pass, this job builds the Python wheel distribution.
    -   **`publisher_release` job**: This job runs only when a version tag (e.g., `v1.2.3`) is pushed. It verifies the tag is on the `master` branch and then publishes the built wheel to PyPI.

## 6. Development Environment Setup and Key Commands

The project uses `hatch` for dependency management and running tasks, and `gh` (GitHub CLI) for interacting with GitHub.

> **Note:** The commands provided throughout this document are intended as examples. It is not always necessary to use them exactly as written. Please adapt them to fit the specific requirements of your task.

> **Tip: Self-Correction and Verification:** If you are unsure about a `hatch` command, or suspect that new subcommands or options may have become available (e.g., after a library update), you should proactively verify the commands by running `hatch --help` or `hatch <command> --help` (e.g., `hatch version --help`). If you discover new or changed commands, you should update this `GEMINI.md` file to ensure the project context remains up-to-date for future AI agents.

### 6.1. Setup Virtual Environment and Install Dependencies

To set up the development environment, first install `pipx` globally, then use it to install `hatch`. Finally, create the project's virtual environment and install all required dependencies (including development and documentation dependencies) using `hatch`.

```bash
# Install pipx globally
pip install pipx
pipx ensurepath

# Install hatch using pipx
pipx install hatch

# Create a virtual environment and install all dependencies
hatch env create dev
```

### 6.2. Running Quality Checks (Linting and Formatting)

The project uses `pre-commit` with `ruff` for code formatting and linting, and `mypy` for type checking to ensure code quality and a consistent style. `gh` (GitHub CLI) is also used for various repository interactions.

```bash
# Install pre-commit hooks (run once after cloning)
hatch run dev:hooks

# Run pre-commit hooks on all files (useful before committing or for manual checks)
hatch run dev:check

# Manually run linting, formatting, and type checking
hatch run dev:lint
hatch run dev:format
hatch run dev:typecheck
```

**Important**: It is crucial to run `hatch run pre-commit run --all-files` after making any changes and before committing. This ensures your code adheres to the project's quality standards. If `pre-commit` reports issues, fix them and re-run until all checks pass.

### 6.3. Dependency Management

`hatch` manages dependencies through its environments. To ensure your environment is synchronized with `pyproject.toml`:

```bash
# Create or update the default environment
hatch env create
# Or, to recreate a specific environment (e.g., 'dev')
hatch env remove dev
hatch env create dev
```

### 6.4. Running Tests

Once tests are added (typically in a `tests/` directory), you can run them using `hatch`.

```bash
# Example of how to run tests with pytest (assuming a 'test' script is defined in pyproject.toml)
hatch run test
```

### 6.5. Building the Package

To distribute or install the library locally, you can build it into a standard Python wheel (`.whl`) file using `hatch`.

```bash
# Run the build process from the project root
hatch build
```
This command will create a `dist/` directory containing the built wheel and a source archive.

### 6.6. Building Documentation

The documentation is built using [Sphinx](https://www.sphinx-doc.org/en/master/) via a Hatch script.

```bash
# Build the HTML documentation
hatch run docs:build
```
The output will be in `docs/_build/html`.

### 6.7. Manual SDK Download

The library is designed to automatically download the TeamTalk SDK on its first run if it's not found. Therefore, running the downloader manually is **not part of the standard workflow**. This command is only for specific troubleshooting scenarios, such as forcing a re-download of the SDK.

```bash
# Run the SDK downloader script directly via hatch
hatch run sdk-download
```

### 6.8. Version Management

The project uses `hatch` to manage its version, which is stored in `pytalk/__init__.py` and dynamically read during the build process.

#### Bumping the Version
To increment the project's version according to semantic versioning, use the following commands:

```bash
# Bump the patch version (e.g., 1.0.0 -> 1.0.1)
hatch version patch

# Bump the minor version (e.g., 1.0.0 -> 1.1.0)
hatch version minor

# Bump the major version (e.g., 1.0.0 -> 2.0.0)
hatch version major
```

#### Setting a Specific Version
You can also set a specific version number directly:

```bash
# Set a specific version
hatch version 2.0.0
```
**Note:** When in doubt about the exact command or its behavior, it is always a good practice to double-check by running `hatch version --help`.

## 7. Standard Development Workflow

To contribute effectively to this project, follow this standard workflow:

1.  **Create a Branch**: Start by creating a new branch from `master` for your feature or fix.
    ```bash
    git checkout -b <branch-name>
    ```
2.  **Implement Changes**: Write your code and make the necessary changes.

3.  **Verify Changes**: Before committing, it is crucial to verify your work by running all quality checks and tests.
    ```bash
    # Run all pre-commit hooks (formatting, linting, etc.)
    hatch run dev:check

    # Manually run linting, formatting, and type checking
    hatch run dev:lint
    hatch run dev:format
    hatch run dev:typecheck

    # Run the test suite (once implemented)
    hatch run dev:test
    ```
    If any of these commands fail, fix the issues and run them again until they all pass.

4.  **Stage and Review Changes**: Review and stage your files for commit.

    ```bash
    # First, check the status to see all modified files
    git status

    # Next, add only the specific files related to your change.
    # Avoid using `git add .` to prevent staging unrelated files.
    git add <path/to/file1> <path/to/file2>

    # Review the exact changes that are staged for commit
    git diff --staged
    ```



5.  **Commit Changes**: Commit your staged changes using the project's conventions.

    To provide a multi-line commit message or one containing special characters, write the message to a temporary file and then use the `-F` flag. This is the **only allowed method** for committing.

    **For Unix-like systems (Linux, macOS, Git Bash):**
    ```bash
    # 1. Create a temporary file and write the commit message to it using `write_file`
    #    (Replace the content with your actual commit message)
    #    Note: The `write_file` tool requires an absolute path.
    #    Example content for commit_message.txt:
    #    "✨ feat(scope): descriptive commit message\n\nDetailed body of the commit message.\n- List changes or reasons here."
    #    The content should be a single string with newlines for multi-line messages.
    #    Example tool call:
    #    print(default_api.write_file(file_path="/path/to/project/commit_message.txt", content="✨ feat(scope): descriptive commit message\n\nDetailed body of the commit message.\n- List changes or reasons here."))

    # 2. Commit using the message from the file
    git commit -F commit_message.txt

    # 3. Delete the temporary file after the commit using `run_shell_command`
    #    Example tool call:
    #    print(default_api.run_shell_command(command="rm commit_message.txt", description="Delete temporary commit message file."))
    ```

    **For Windows (Command Prompt/PowerShell):**
    ```cmd
    :: 1. Create a temporary file and write the commit message to it using `write_file`
    ::    (Replace the content with your actual commit message)
    ::    Note: The `write_file` tool requires an absolute path.
    ::    Example content for commit_message.txt:
    ::    "✨ feat(scope): descriptive commit message\n\nDetailed body of the commit message.\n- List changes or reasons here."
    ::    The content should be a single string with newlines for multi-line messages.
    ::    Example tool call:
    ::    print(default_api.write_file(file_path="C:\\path\\to\\project\\commit_message.txt", content="✨ feat(scope): descriptive commit message\n\nDetailed body of the commit message.\n- List changes or reasons here."))

    :: 2. Commit using the message from the file
    git commit -F commit_message.txt

    :: 3. Delete the temporary file after the commit using `run_shell_command`
    ::    Example tool call:
    ::    print(default_api.run_shell_command(command="del commit_message.txt", description="Delete temporary commit message file."))
    ```


6.  **Push Branch**: Push your local branch to the remote repository.

    ```bash

    git push --set-upstream origin <branch-name>

    ```



7.  **Create a Pull Request (PR)**: On GitHub, open a Pull Request from your branch to `master`. Use the `gh` CLI for convenience.

    ```bash

    gh pr create --base master --head <branch-name> --title "✨ feat(scope): descriptive PR title" --body "Detailed description of changes."

    ```



8.  **GitHub CLI Integration**: After creating a PR, you can use `gh` to track its status, investigate CI/CD runs, and manage related issues without leaving the command line.



    **Tracking Pull Requests:**

    ```bash

    # Display the status of your PRs and PRs waiting for your review

    gh pr status



    # Open the current branch's PR in the web browser

    gh pr view --web

    ```



    **Investigating CI/CD Runs:**

    If a check fails, you can inspect the logs directly in your terminal.

    ```bash

    # List the most recent runs for the current branch

    gh run list



    # List only the failed runs for the current branch

    gh run list --status failure



    # View the details and logs of a specific run (replace RUN_ID)

    gh run view RUN_ID --log



    # Watch a run in real-time

    gh run watch

    ```



    **Managing Issues:**

    ```bash

    # List all open issues in the repository

    gh issue list



    # View a specific issue in the browser

    gh issue view ISSUE_ID --web

    ```



9.  **Merge PR**: After the PR is reviewed and all CI checks pass, merge it into `master`.



10. **Update Local `master`**: Switch back to your local `master` branch and pull the latest changes.

    ```bash

    git checkout master

    git pull

    ```



11. **Clean Up**: Delete your local feature branch.

    ```bash

    git branch -d <branch-name>

    ```
