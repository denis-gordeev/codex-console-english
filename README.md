# codex-console

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

### Next Iterations

- Continue polishing wording consistency in logs, tests, and low-traffic routes as new gaps are found.
- Expand regression coverage for translated API messages and settings flows.
- Add API tests for the login gate and authenticated page redirects.
- Review remaining English copy for awkward machine-translated phrasing in backend logs and route docstrings.
- Verify Docker environment variable examples against the actual `settings` names used by the app.

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

You can edit environment variables in [docker-compose.yml](/Users/denis/programming/codex-console-english/docker-compose.yml), such as the port and access password.

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

`codex-console`

## Disclaimer

This project is for learning, research, and technical discussion only. Please follow the relevant platform rules and terms of service, and do not use it for abuse, violations, or illegal activity.

Any risks or consequences resulting from use of this project are the responsibility of the user.
