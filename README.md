# codex-console-english

An actively maintained, compatibility-focused fork of [cnlimiter/codex-manager](https://github.com/cnlimiter/codex-manager).

The goal of this fork is simple: fix the parts of the recent OpenAI registration flow that became unreliable, so registration, login, token retrieval, and packaged execution work more consistently.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

## Community

- Group chat: https://qm.qq.com/q/ZTCKxawxeo

## Acknowledgments

Thanks to the original author, [cnlimiter](https://github.com/cnlimiter), for the upstream project and foundation.

This repository keeps the original structure and overall approach, while applying compatibility fixes, flow updates, and usability improvements. It is intended to be a practical maintained fork that still works with the current flow.

## Progress Tracker

### Completed

- Rewrote the public `README.md` into clear English and aligned it with the current project positioning.
- Translated the main web app surface, settings UI, task manager copy, and Outlook service/provider layers into English.
- Normalized several user-facing success and error messages so tests and runtime behavior use the same language.
- Added and updated tests around CPA upload URL normalization and DuckMail service wiring.
- Migrated remaining Pydantic response models from class-based `Config` to `ConfigDict`.
- Replaced FastAPI `@app.on_event(...)` startup and shutdown hooks with a lifespan handler.
- Added a regression test to verify the app lifespan initializes shared runtime state on startup.
- Expanded Web UI auth regressions to cover the dashboard route, logout cookie clearing, and redirect behavior for already authenticated `/login` visits.
- Improved the login UX so authenticated sessions are sent straight to the requested in-app page instead of seeing the password form again.
- Fixed the "Agent" → "Proxy" mistranslation across all settings, routes, database models, CRUD operations, and service modules.
- Replaced "Mailbox" with "Email" across all service modules, routes, models, and user-facing messages for consistent terminology.
- Cleaned up awkward English in setting descriptions ("Whether to enable X" → "Enable X"), section headers, and docstrings across settings.py and constants.py.
- Polished error messages in constants.py for conciseness ("Account does not exist" → "Account not found", "OpenAI interface current limit" → "OpenAI API rate limit").
- Standardized comment style in settings.py, constants.py, and models.py (fixed missing spaces after #, consistent terminology).
- Improved route-level English in settings.py, email.py, registration.py, and accounts.py (concise error messages, consistent naming).
- Refined service module docstrings and log messages (base.py, moe_mail.py, tempmail.py, temp_mail.py, duck_mail.py, freemail.py, imap_mail.py, outlook/).
- Replaced "encapsulation" → "wrapper", "regular expression" → "regex pattern", "current limiting" → "rate limiting" across core and service modules.
- Replaced all "domain name" with "domain" across frontend templates, JS, route labels, and service docstrings for consistent terminology.
- Replaced all remaining "Mailbox" and "mailbox" with "Email" / "email" in user-facing UI labels, comments, log messages, and route descriptions.
- Changed "Customized email service" → "Custom email service" and "Temporary Mailbox" → "Temp Mail" for conciseness.
- Fixed remaining "Agent" → "Proxy" mistranslation in settings.js and settings.html (user-facing strings, comments, toast messages).
- Replaced "self-deployed" → "self-hosted" across all frontend and backend files for standard English terminology.
- Replaced "mailing list" → "list of emails" / "email list" across all Outlook and email service modules.
- Replaced "interface" → "API"/"endpoint" where the Chinese term for "interface" was mistranslated in REST API context.
- Replaced "private domain" → "custom domain" in DuckMail service description.
- Fixed "Verification code waiting for configuration" → "Verification code retrieval configuration" for clarity.
- Replaced "deduplication mechanism/collection" → "dedup tracking/set" for concise terminology.
- Fixed "Get the quantity" → "Number of emails to fetch", "whether to only get unread" → "Fetch only unread emails", and similar awkward phrasing.
- Polished error messages ("The number of registrations must be between 1-100" → "Registration count must be between 1 and 100").
- Polished log messages across Outlook, moe_mail, freemail, temp_mail, websocket, and task_manager for natural English.
- Fixed "Is the connection normal?" → "True if the connection is working", "Configuration information" → "Configuration dictionary", "timeout time" → "Timeout (seconds)".
- Replaced non-ASCII ▼ with &darr; in app.js multi-select dropdown.
- Fixed 154 JS comment spacing issues (missing space after `//`) across all 6 frontend JS files.
- Replaced non-ASCII em dash with ASCII `--` in session.py docstring for ASCII compatibility.
- Fixed 54 docstring/translation artifacts: "initialization provider" → "Initialize the provider", "Respond to JSON data" → "Response JSON data", "Parsing JWT" → "Parse JWT", "Handling OAuth callbacks" → "Handle OAuth callback", "REST API interface" → "REST API", and 49 more.
- Replaced all "does not exist" with "not found" in HTTP 404 error messages (34 occurrences across 9 files) for standard REST API conventions.
- Replaced "based on" with "by" in CRUD docstrings (6 occurrences) for idiomatic English.
- Polished 20 awkward log messages in registration routes and register engine for natural English.
- Fixed formatting bug in models.py (two column definitions on one line).
- Added missing space after emoji in settings.html.
- Replaced "automatic registration system" with "Auto-Registration System" for title-case consistency across 6 files.
- Replaced all "Verification code" compound terms with "OTP" (34 occurrences) for concise standard terminology.
- Replaced "obtain" with "get" in 21 log messages and docstrings for natural English.
- Fixed "topic" → "subject" mistranslation (Chinese for "topic") in email parser and settings (6 occurrences).
- Replaced "covert matching" → "fallback matching" and "Bottom line" → "Fallback" in email extraction strategy.
- Replaced "Mail parser" → "Email parser" and "New version of IMAP" → "New IMAP" for conciseness.
- Standardized "Whether the X" → statement form in 13 comments/docstrings.
- Replaced "Verification" → "Validation" / "Authentication" in 12 UI and API contexts (login page, token validation, sender validation).
- Replaced "Execute" → "Run", "synchronization tasks" → "synchronous tasks" in registration routes.
- Replaced "configuration items/parameters" → "settings/options" across 9 occurrences.
- Replaced "collection" → "set" (mistranslation of the Chinese term for "set") and "dedup" → "deduplication" in JS.
- Fixed "Is the connection successful?" → "True if connection is successful" across 3 provider docstrings.
- Fixed 4 missing spaces after # in Python comments and 1 missing space after emoji in index.html.
- Replaced all remaining "verification code" with "OTP" across backend services, routes, and frontend (~100 occurrences).
- Replaced "whether" → "if/True if" in 12 docstrings, comments, and JS strings.
- Fixed gerund-as-imperative patterns in 11 log messages and comments ("Creating" → "Create", "Processing" → "Process", etc.).
- Fixed stilted phrasing in 22 locations ("Get the definition of" → "Get a", "the connection of the first account" → "the first account's connection", etc.).
- Replaced "obtain" → "get/retrieve" in 7 locations across JS and Python.
- Standardized batch task completion messages ("[Complete]" → "[Done]", "Success/Failure" → "Succeeded/Failed").
- Replaced remaining "Verification code" with "OTP" in error messages, log messages, comments, and section headers (5 occurrences).
- Replaced "whether" → "if/True if" in 12 more docstrings, comments, and route descriptions.
- Replaced "email information" → "email data" across all service modules and frontend JS (10 occurrences).
- Replaced "the health status of all providers" → "all provider health statuses" for consistent possessive form (4 occurrences).
- Replaced "Regular expressions" → "Regex patterns" in constants.py section header.
- Replaced "Get the message list in your email" → "Get the email message list" in moe_mail.py.
- Fixed "Synchronous registration tasks executed in the thread pool" → "Synchronous registration task run in the thread pool".
- Fixed "Database backup succeeded" → "Database backup successful" and similar standalone message patterns.
- Replaced all "has been" + past participle Chinese-style passive constructions with natural English active forms across backend and frontend (~65 occurrences: "Task has been canceled" → "Task canceled", "Service has been deleted" → "Service deleted", etc.).
- Replaced "Noun + failed" Chinese-English pattern with "Failed to + verb" across all JS files (~31 occurrences: "Save failed" → "Failed to save", "Add failed" → "Failed to add", etc.).
- Replaced "concurrencies" / "number of concurrency" → "concurrent tasks" / "concurrency" for standard English (4 occurrences).
- Replaced "corresponding" → "matching"/"for" where the Chinese term for "corresponding" was mistranslated (4 occurrences).
- Replaced "lacks Token" → "has no token" across accounts.py and upload modules (4 occurrences).
- Replaced "real-time push" → "live delivery/updates" in task manager and WebSocket routes (4 occurrences).
- Replaced "restore" → "re-enable" for disabled provider recovery context in health checker (4 occurrences).
- Replaced "configuration dictionary, supports the following keys:" → "configuration dictionary with the following keys:" across all service modules (6 occurrences).
- Replaced "Sensitive fields are not returned" → "Sensitive fields are omitted" and similar passive-to-active fixes in email.py.
- Replaced "cross-page navigation" → "navigating away and back" in app.js (4 occurrences).
- Replaced "downgrade scenario" → "fallback scenario" and "Service connection is normal" → "Service connection OK" in JS files.
- Replaced "passed in" → "provided", "front end" → "frontend", "Logout WebSocket" → "Unregister/disconnect WebSocket" for consistent terminology.
- Replaced "according to" → "by" and "concurrencies" → "concurrent tasks" for idiomatic English in routes.
- Replaced "OTP sending timestamp" → "OTP send timestamp" / "Timestamp when the OTP was sent" for natural English (5 occurrences).
- Replaced "modal box" → "modal" across all HTML templates and JS files (13 occurrences).
- Unified "leave blank to remain unchanged" / "leave blank to not modify" / "Leave blank to keep the original value" → "Leave blank to keep current" (~25 occurrences).
- Replaced "Please fill in" → "Please enter" in JS (8 occurrences).
- Replaced "heartbeat detection" → "heartbeat check/ping" in WebSocket routes (5 occurrences).
- Replaced "configuration" → "settings" in UI headers, toasts, and labels across HTML and JS (13 occurrences).
- Replaced "exit IP" → "outgoing IP" in proxy test messages (2 occurrences).
- Replaced "request header name" → "header name" in settings and service modules (4 occurrences).
- Replaced "on re-login" → "during re-login" in registration engine (4 occurrences).
- Replaced "fill in" / "is not filled in" → "enter" / "is not provided" in HTML and JS (11 occurrences).
- Replaced Noun+failed patterns in error constants ("Network connection failed" → "Failed to connect to network", etc.).
- Replaced "password/authorization code" → "password/app password" in email service UI.
- Replaced "forced direct connection" → "direct connection required" in IMAP service.
- Replaced "skip repeated registration" → "skip duplicate registration" in task manager.
- Replaced various stilted JS patterns ("page reactivated" → "Page became visible again", "Batch detection" → "Batch subscription check", etc.).

### Next Iterations

- Continue polishing wording consistency in logs, tests, and low-traffic routes.
- Expand regression coverage for translated API messages and settings flows.
- Add API tests for access-control edge cases such as malformed cookies and custom logout `next` targets.
- Verify Docker environment variable examples against the actual `settings` names used by the app.
- Add focused tests for the settings save flows and error messages returned by low-traffic API endpoints.
- Verify that all "Account not found" / "X not found" HTTP 404 messages are consistent with test assertions.

## What This Branch Fixes

To match the current registration flow, this branch mainly addresses the following issues:

1. Sentinel POW support

   OpenAI now enforces Sentinel POW validation. Passing an empty value is no longer enough, so this branch adds an actual POW solving flow.

2. Registration and login are handled separately

   Registration often no longer returns a usable token immediately. Instead, it may redirect to phone binding or another follow-up step.

   This branch changes the flow to: register successfully first, then run a separate login flow to obtain the token. That avoids getting stuck in the old logic.

3. Duplicate verification email sending removed

   During login, the server already sends the verification email automatically. The old logic sent another one manually, which could cause code conflicts.

   This branch now waits for the verification email sent by the system.

4. Re-login flow page handling fixed

   The login entry and password submission logic were updated to match recent page flow changes, reducing cases where the process gets stuck on the wrong page.

5. Terminal and Web UI copy improved

   Error and status messages were made more readable and less hostile while keeping the same operational meaning.

## Core Features

- Web UI for managing registration tasks and account data
- Batch registration support
- Real-time log viewing
- Basic task management
- Multiple email service integrations
- SQLite and remote PostgreSQL support
- Packaging for Windows, Linux, and macOS executables
- Better compatibility with the current OpenAI registration and login flow

## Requirements

- Python 3.10+
- `uv` (recommended) or `pip`

## Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -r requirements.txt
```

## Environment Variables

Optional. Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

Common variables for `.env`:

| Variable | Description | Default |
| --- | --- | --- |
| `APP_HOST` | Bind host | `0.0.0.0` |
| `APP_PORT` | Bind port | `8000` |
| `APP_ACCESS_PASSWORD` | Web UI access password | `admin123` |
| `APP_DATABASE_URL` | Database connection string | `data/database.db` |

Priority order:

`CLI arguments > environment variables (.env) > database settings > defaults`

Additional runtime overrides:

- `WEBUI_HOST`, `WEBUI_PORT`, and `WEBUI_ACCESS_PASSWORD` are also supported when they already exist in the process environment, which is useful for Docker and other container runtimes.
- `DATABASE_URL` is also supported as a fallback alias for `APP_DATABASE_URL`.

## Start The Web UI

```bash
# Default start (127.0.0.1:8000)
python webui.py

# Specify host and port
python webui.py --host 0.0.0.0 --port 8080

# Debug mode (hot reload)
python webui.py --debug

# Set the Web UI access password
python webui.py --access-password mypassword

# Combine options
python webui.py --host 0.0.0.0 --port 8080 --access-password mypassword
```

Notes:

- `--access-password` takes precedence over the password stored in the database
- It only applies to the current launch
- The packaged executable also supports this argument
- `.env` files should use `APP_*` keys; container environments may use either `APP_*` or `WEBUI_*`, but the Docker examples in this repository use `WEBUI_*`

Example:

```bash
codex-console.exe --access-password mypassword
```

Then open:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

## Docker Deployment

### Using docker-compose

```bash
docker-compose up -d
```

You can edit environment variables in [docker-compose.yml](/Users/denis/programming/autowork/codex-console-english/docker-compose.yml), such as the port and access password.

### Using docker run

```bash
docker run -d \
  -p 1455:1455 \
  -e WEBUI_HOST=0.0.0.0 \
  -e WEBUI_PORT=1455 \
  -e WEBUI_ACCESS_PASSWORD=your_secure_password \
  -v $(pwd)/data:/app/data \
  --name codex-console \
  ghcr.io/<yourname>/codex-console:latest
```

Notes:

- `WEBUI_HOST`: bind host, default `0.0.0.0`
- `WEBUI_PORT`: bind port, default `1455`
- `WEBUI_ACCESS_PASSWORD`: Web UI access password
- `DEBUG`: set to `1` or `true` to enable debug mode
- `LOG_LEVEL`: log level, for example `info` or `debug`

`-v $(pwd)/data:/app/data` is important. It persists the database and account data on the host. Without it, your data may disappear when the container restarts.

## Using Remote PostgreSQL

```bash
export APP_DATABASE_URL="postgresql://user:password@host:5432/dbname"
python webui.py
```

`DATABASE_URL` is also supported, but it has lower priority than `APP_DATABASE_URL`.

## Build An Executable

```bash
# Windows
build.bat

# Linux/macOS
bash build.sh
```

After a successful Windows build, the output in `dist/` will look like:

```text
dist/codex-console-windows-X64.exe
```

If packaging fails, check:

- Whether Python is in `PATH`
- Whether all dependencies are installed
- Whether antivirus software blocked the PyInstaller artifact
- Whether the terminal output contains a more specific error

## Project Positioning

This repository is best understood as:

- A repaired and enhanced fork of the original project
- A compatibility-maintained version for the current registration flow
- A practical base for your own secondary development

If you plan to publish it publicly, it is a good idea to make the origin explicit in the repository description:

`Forked and fixed from cnlimiter/codex-manager`

That makes the source clearer for other users and gives proper credit to the upstream author.

## Repository Name

Current repository name:

`codex-console-english`

The packaged application and container examples still use the runtime name `codex-console`.

## Disclaimer

This project is for learning, research, and technical discussion only. Please follow the relevant platform rules and terms of service, and do not use it for abuse, violations, or illegal activity.

Any risks or consequences resulting from use of this project are the responsibility of the user.
