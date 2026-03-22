# codex-console

An enhanced version based on continuous fixes and maintenance from [cnlimiter/codex-manager](https://github.com/cnlimiter/codex-manager).

The goal of this version is very straightforward: to make up for the pitfalls in the recent OpenAI registration link that "it was still running yesterday, but suddenly crashed today", making registration, login, token acquisition, and packaged operation more stable.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)

##QQGroup

- Communication group: https://qm.qq.com/q/ZTCKxawxeo

## Acknowledgments

First of all, I would like to thank the upstream project author [cnlimiter](https://github.com/cnlimiter) for providing excellent basic projects.

This warehouse is based on the original project ideas and structure for compatibility repair, process adjustment and experience optimization, and is suitable for continued use as a "currently available repair and maintenance version".

## What is fixed in this branch?

In order to adapt to the current registration link, this branch focuses on the following issues:

1. Added Sentinel POW solution logic
OpenAI will now forcefully verify Sentinel POW. It is no longer possible to pass null values ​​​​directly. The actual solution process is supplemented here.

2. Split registration and login into two sections
Now after the registration is completed, the available token is usually not returned directly, but jumps to the bound mobile phone or subsequent page.
This branch is changed to "Successfully register first, then go through the login process separately to get the token" to avoid getting stuck in the old logic.

3. Remove repeated sending of verification codes
During the login process, the server itself will automatically send a verification code email, and the old logic will be sent manually again, which can easily lead to conflicts between the old and new verification codes.
Now change it to waiting for the verification code email automatically sent by the system.

4. Fix the page judgment problem in the re-login process
In response to changes in page flow when logging in again, the login entrance and password submission logic have been adjusted to reduce the situation of being stuck on the wrong page.

5. Optimize terminal and Web UI prompt copywriting
While retaining readability, change some prompts to be more friendly, so that at least you won't feel like you are being scolded when you make a mistake.

##Core competencies

- Web UI manages registration tasks and account data
- Supports batch registration, real-time log viewing, and basic task management
- Support multiple email services to receive codes
- Supports SQLite and remote PostgreSQL
- Supports packaging into Windows/Linux/macOS executable files
- More adapted to the current OpenAI registration and login links

##Environmental requirements

- Python 3.10+
- `uv` (recommended) or `pip`

## Install dependencies

```bash
# Use uv (recommended)
uv sync

# or use pip
pip install -r requirements.txt
```## Environment variable configuration

Optional. copy`.env.example`for`.env`Modify as needed:```bash
cp .env.example .env
```Commonly used variables are as follows:

| variable | description | default value |
| --- | --- | --- |
|`APP_HOST`| Listening host |`0.0.0.0` |
| `APP_PORT`| Listening port |`8000` |
| `APP_ACCESS_PASSWORD`| Web UI Access Key |`admin123` |
| `APP_DATABASE_URL`| Database connection string |`data/database.db`|

Priority:`Command line parameters > Environment variables (.env) > Database settings >Default value`

## Start Web UI

```bash
# Start by default (127.0.0.1:8000)
pythonwebui.py

# Specify address and port
python webui.py --host 0.0.0.0 --port 8080

# Debug mode (hot reload)
python webui.py --debug

# Set Web UI access key
python webui.py --access-password mypassword

# Combination parameters
python webui.py --host 0.0.0.0 --port 8080 --access-password mypassword
```illustrate:

-`--access-password`takes precedence over key settings in the database
- This parameter only takes effect for this startup
- Packaged exe also supports this parameter

For example:```bash
codex-console.exe --access-password mypassword
```After startup visit:

[http://127.0.0.1:8000](http://127.0.0.1:8000)

## Docker deployment

### Use docker-compose```bash
docker-compose up -d
```you can`docker-compose.yml`Modify environment variables, such as ports and access passwords.

### Use docker run```bash
docker run -d \
  -p 1455:1455 \
  -e WEBUI_HOST=0.0.0.0 \
  -e WEBUI_PORT=1455 \
  -e WEBUI_ACCESS_PASSWORD=your_secure_password \
  -v $(pwd)/data:/app/data \
  --name codex-console \
  ghcr.io/<yourname>/codex-console:latest
```illustrate:

-`WEBUI_HOST`: Listening host, default`0.0.0.0`
- `WEBUI_PORT`: Listening port, default`1455`
- `WEBUI_ACCESS_PASSWORD`: Web UI access password
-`DEBUG`: set to`1`or`true`Debug mode can be enabled
-`LOG_LEVEL`: Log level, for example`info`,`debug`Notice:`-v $(pwd)/data:/app/data`Very important, this will persist the database and account data to the host machine. Otherwise, the data may disappear as soon as the container is restarted.

## Use remote PostgreSQL```bash
export APP_DATABASE_URL="postgresql://user:password@host:5432/dbname"
python webui.py
```Also supports`DATABASE_URL`, but with a lower priority than`APP_DATABASE_URL`.

##Package into executable file```bash
# Windows
build.bat

# Linux/macOS
bash build.sh
```After Windows packaging is completed, it will be in`dist/`The directory generates files similar to the following:```text
dist/codex-console-windows-X64.exe
```If packaging fails, check first:

- Whether Python has been added to PATH
- Whether the dependencies are installed completely
- Whether the anti-virus software blocks the PyInstaller product
- Is there a more specific error log in the terminal?

##Project positioning

This repository is better suited as:

- A restored and enhanced version of the original project
- Compatible maintenance version of the current registered link
-Basic version developed by myself

If you plan to release it publicly, it is recommended to explicitly write in the repository description:`Forked and fixed from cnlimiter/codex-manager`This not only makes it easier for others to understand the source, but also gives more respect to the upstream author.

## Warehouse naming

Current warehouse name:`codex-console`

## Disclaimer

This project is only for learning, research and technical exchange. Please abide by the relevant platform and service terms and do not use it for illegal, abusive or illegal purposes.

Any risks and consequences arising from the use of this project are borne by the user.
