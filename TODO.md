# TODO

## Completed In This Round (June 14, 2026 - Round 37)

- Pulled `origin/main` - repository was already up to date.
- Deep scan found ~154 substantive translation artifacts (awkward English, mistranslations, inconsistent terminology) that previous rounds had missed.
- Fixed the remaining "Agent" → "Proxy" mistranslation in settings.js (13 occurrences: comments, toast messages, confirm dialogs) and settings.html (3 occurrences: section headers, empty-state text, subtitle).
- Replaced "self-deployed" → "self-hosted" across all files (15 occurrences in email_services.js, app.js, utils.js, email_services.html, email.py routes, temp_mail.py, freemail.py, registration.py).
- Replaced "mailing list" → "list of emails" / "email list" across all Outlook service modules and email parser (15 occurrences in service.py, base.py, graph_api.py, imap_new.py, imap_old.py, email_parser.py, outlook_legacy_mail.py, moe_mail.py, base.py, tempmail.py).
- Replaced "interface" → "API"/"endpoint" where Chinese "接口" was mistranslated (8 occurrences in temp_mail.py, freemail.py, email.py routes, cpa_upload.py).
- Replaced "private domain" → "custom domain" in email.py routes (DuckMail description).
- Fixed "Verification code waiting for configuration" → "Verification code retrieval configuration" in settings.html, settings.js, settings.py, and Python service modules (6 occurrences).
- Replaced "deduplication mechanism/collection" → "dedup tracking/set" across Outlook services, app.js, and settings.html (11 occurrences).
- Fixed "Get the quantity" → "Number of emails to fetch" across Outlook provider docstrings (8 occurrences).
- Fixed "Whether to enable prefix" → "Enable prefix", "whether to only get unread" → "Fetch only unread emails" and similar awkward "whether" patterns (15 occurrences).
- Fixed "encapsulation" → "wrapper" in utils.js.
- Replaced non-ASCII ▼ → &darr; in app.js multi-select dropdown.
- Polished error messages: "The number of registrations must be between 1-100" → "Registration count must be between 1 and 100", "The number of concurrency must be between 1-50" → "Concurrency must be between 1 and 50".
- Polished log messages across Outlook, moe_mail, freemail, temp_mail, websocket, and task_manager modules for natural English phrasing.
- Fixed "Is the connection normal?" → "True if the connection is working" across Outlook provider docstrings.
- Fixed "Configuration information" → "Configuration dictionary", "timeout time" → "Timeout (seconds)" across docstrings.
- Fixed "admin mode management" → "admin-managed" in temp_mail.py and email.py routes.
- Fixed comment spacing (#Extract → # Extract) in token_refresh.py.
- Verified all 32 tests pass successfully (pytest on Python 3.10 via .venv).

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts) - zero non-English language text found.
- Replaced all "domain name" with "domain" across frontend templates (email_services.html), JS (app.js, email_services.js), route labels (email.py), service docstrings (base.py, freemail.py, moe_mail.py, temp_mail.py), and route comments (accounts.py) for consistent terminology.
- Replaced all remaining "Mailbox" / "mailbox" with "Email" / "email" in user-facing UI labels, JS comments, log messages, route descriptions, and template text (accounts.js, accounts.html, app.js, email_services.js, settings.js, utils.js, index.html, settings.html, accounts.py, email.py).
- Changed "Customized email service" → "Custom email service", "Customized mailbox" → "Custom email", "Temporary Mailbox" → "Temp Mail", "Enable temporary mailbox" → "Enable temp mail" for conciseness.
- Updated README.md progress tracker: added completed items and removed the now-resolved "domain name" next-iteration item.
- Verified all 32 tests pass successfully (pytest on Python 3.10 via .venv).

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts) - zero non-English language text found.
- Fixed the "Agent" → "Proxy" mistranslation across settings.py, routes/settings.py, routes/registration.py, database/crud.py, database/models.py, core/http_client.py, and web routes. The proxy settings were labeled "Agent" (a Chinese→English mistranslation) instead of "Proxy".
- Replaced "Mailbox" with "Email" across all service modules (base.py, moe_mail.py, tempmail.py, temp_mail.py, duck_mail.py, freemail.py, imap_mail.py, outlook_legacy_mail.py, outlook/), routes (email.py, registration.py, settings.py), and models.py for consistent terminology.
- Cleaned up setting descriptions in settings.py ("Whether to enable X" → "Enable X", "Web UI Key" → "Web UI secret key", "Custom domain name API address" → "Custom domain API URL").
- Polished error messages in constants.py for conciseness ("Account does not exist" → "Account not found", "Task does not exist" → "Task not found", "OpenAI interface current limit" → "OpenAI API rate limit", "Verification code is invalid" → "Invalid verification code").
- Standardized section headers in constants.py ("enumeration type" → "Enumerations", "Apply constants" → "Application constants", "related constants" → "constants", singular → plural where appropriate).
- Improved route-level English in settings.py ("Proxy does not exist" → "Proxy not found", "Proxy has been deleted" → "Proxy deleted", "export IP" → "exit IP", "Temporary mailbox" → "Tempmail").
- Refined service module docstrings (base.py: "abnormality" → "error", "regular expression" → "regex pattern"; outlook_legacy_mail.py: "current limiting" → "rate limiting", "Does OAuth2 support" → "Whether OAuth2 is supported").
- Replaced "encapsulation" → "wrapper" in core/http_client.py.
- Fixed missing spaces after # in comments across multiple files (models.py, register.py, accounts.py, utils.py, tempmail.py, outlook_legacy_mail.py, session.py, init_db.py).
- Updated README.md progress tracker with completed items and refined next-iteration items.
- Verified all 32 tests pass successfully (pytest on Python 3.10 via .venv).

- Pulled `origin/main` - repository was already up to date.
- Reviewed the current `README.md` progress tracker and advanced one unfinished iteration instead of doing another scan-only round.
- Improved Web UI login flow so authenticated sessions that revisit `/login` are redirected to their requested local page immediately.
- Expanded auth regression coverage in `tests/test_app_lifespan.py` to cover the protected dashboard route, logout cookie clearing, and re-authentication after logout.
- Updated `README.md` progress and next-iteration items so documented status matches the codebase again.
- Added new follow-up plan items for malformed auth-cookie handling, logout redirect edge cases, and settings/API regression coverage.

## Completed In This Round (June 11, 2026 - Round 33)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts) - zero non-English language text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 11, 2026 - Round 32)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts) - zero non-English language text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 10, 2026 - Round 31)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts) - zero non-English language text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 10, 2026 - Round 30)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts) - zero non-English language text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 9, 2026 - Round 29)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts) - zero non-English language text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 8, 2026 - Round 28)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts) - zero non-English language text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 8, 2026 - Round 27)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, non-ASCII artifacts) - zero non-English language text found.
- Replaced box-drawing characters with ASCII dashes in `.env.example:4,14` for ASCII compatibility.
- Replaced Unicode arrows with HTML entities in `templates/accounts.html:195,199` (`←` → `&larr;`, `→` → `&rarr;`).
- Replaced Unicode arrow with HTML entity in `templates/settings.html:529` (`→` → `-&gt;`).
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 5, 2026 - Round 26)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Fixed inconsistent casing in `templates/settings.html:45`: changed `💾 database` to `💾 Database` to match title-case style of all other tab buttons.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 3, 2026 - Round 25)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 3, 2026 - Round 24)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 2, 2026 - Round 23)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 2, 2026 - Round 22)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (June 1, 2026 - Round 21)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (May 30, 2026 - Round 20)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (May 29, 2026 - Round 19)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (May 29, 2026 - Round 18)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (May 28, 2026 - Round 17)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (May 28, 2026 - Round 16)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, Thai, non-ASCII artifacts, invisible zero-width characters) - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (May 27, 2026 - Round 15)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for non-English text (Cyrillic, CJK, Arabic, and non-ASCII artifacts) - zero non-English language text found.
- Fixed invisible zero-width space characters (U+200B) in comment at `src/config/constants.py:223`.
- Replaced Unicode arrow `→` with ASCII `->` in comment at `src/services/moe_mail.py:108` for ASCII compatibility.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new non-English text to translate.

## Completed In This Round (May 26, 2026 - Round 14)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian, Han, Hangul, and Arabic text across all source file types - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new changes to translate.
- All test categories passing:
  - App lifespan and authentication flows (9 tests)
  - CPA upload URL normalization (4 tests)
  - DuckMail service integration (2 tests)
  - Email service DuckMail routes (4 tests)
  - Payment link generation with English headers (2 tests)
  - Registration engine with Sentinel POW support (3 tests)
  - Static asset versioning and English locale usage (5 tests)

## Completed In This Round (April 15, 2026 - Round 13)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text across all Python source files, HTML templates, documentation, configuration files, shell scripts, and batch files - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new changes to translate.
- All test categories passing:
  - App lifespan and authentication flows (9 tests)
  - CPA upload URL normalization (4 tests)
  - DuckMail service integration (2 tests)
  - Email service DuckMail routes (4 tests)
  - Payment link generation with English headers (2 tests)
  - Registration engine with Sentinel POW support (3 tests)
  - Static asset versioning and English locale usage (5 tests)

## Completed In This Round (April 14, 2026 - Round 12)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text across all Python source files, HTML templates, documentation, configuration files, shell scripts, and batch files - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new changes to translate.
- All test categories passing:
  - App lifespan and authentication flows (6 tests)
  - CPA upload URL normalization (4 tests)
  - DuckMail service integration (2 tests)
  - Email service DuckMail routes (4 tests)
  - Payment link generation with English headers (2 tests)
  - Registration engine with Sentinel POW support (3 tests)
  - Static asset versioning and English locale usage (5 tests)

## Completed In This Round (April 14, 2026 - Round 11)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text across all Python source files, HTML templates, documentation, configuration files, shell scripts, and batch files - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new changes to translate.
- All test categories passing:
  - App lifespan and authentication flows (6 tests)
  - CPA upload URL normalization (4 tests)
  - DuckMail service integration (2 tests)
  - Email service DuckMail routes (4 tests)
  - Payment link generation with English headers (2 tests)
  - Registration engine with Sentinel POW support (3 tests)
  - Static asset versioning and English locale usage (5 tests)

## Completed In This Round (April 13, 2026 - Round 10)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text across all Python source files, HTML templates, and documentation - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new changes to translate.
- All test categories passing:
  - App lifespan and authentication flows (6 tests)
  - CPA upload URL normalization (4 tests)
  - DuckMail service integration (2 tests)
  - Email service DuckMail routes (4 tests)
  - Payment link generation with English headers (2 tests)
  - Registration engine with Sentinel POW support (3 tests)
  - Static asset versioning and English locale usage (5 tests)

## Completed In This Round (April 13, 2026 - Round 9)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text using comprehensive grep across .py, .md, .txt, .json, .yaml, .toml, .html, .sh, .spec, Dockerfile, .yml, .cfg, .ini, .env - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new changes to translate.
- All test categories passing:
  - App lifespan and authentication flows (6 tests)
  - CPA upload URL normalization (4 tests)
  - DuckMail service integration (2 tests)
  - Email service DuckMail routes (4 tests)
  - Payment link generation with English headers (2 tests)
  - Registration engine with Sentinel POW support (3 tests)
  - Static asset versioning and English locale usage (5 tests)

## Completed In This Round (April 12, 2026 - Round 8)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text using comprehensive ASCII-range grep across .py, .md, .txt, .json, .yaml, .toml, .html, .sh, .spec, Dockerfile, .yml, .cfg, .ini, .env - zero non-English text found.
- Confirmed repository translation status remains complete; no new changes to translate.
- All source code, documentation, configuration, templates, and scripts are fully English.

## Completed In This Round (April 12, 2026 - Round 7)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text using `git grep` across .py, .md, .txt, .json, .yaml, .toml, .html, .sh, .spec, Dockerfile, .yml, .cfg, .ini, .env - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new changes to translate.
- All test categories passing:
  - App lifespan and authentication flows (6 tests)
  - CPA upload URL normalization (4 tests)
  - DuckMail service integration (2 tests)
  - Email service DuckMail routes (4 tests)
  - Payment link generation with English headers (2 tests)
  - Registration engine with Sentinel POW support (3 tests)
  - Static asset versioning and English locale usage (5 tests)

## Completed In This Round (April 11, 2026 - Round 6)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text using `git grep` and `rg` across .py, .md, .txt, .json, .yaml, .toml, .html, .sh, .spec, Dockerfile, config files - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via .venv).
- Confirmed repository translation status remains complete; no new changes to translate.
- All test categories passing:
  - App lifespan and authentication flows (6 tests)
  - CPA upload URL normalization (4 tests)
  - DuckMail service integration (2 tests)
  - Email service DuckMail routes (4 tests)
  - Payment link generation with English headers (2 tests)
  - Registration engine with Sentinel POW support (3 tests)
  - Static asset versioning and English locale usage (5 tests)

## Completed In This Round (April 11, 2026 - Round 5)

- Pulled `origin/main` - repository was already up to date.
- Scanned all tracked files for Cyrillic/Russian text using `git grep` across .py, .md, .txt, .json, .yaml, .toml, .html, .sh, .spec, Dockerfile - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via uv).
- Confirmed repository translation status remains complete; no new changes to translate.

## Completed In This Round (April 10, 2026 - Round 4)

- Pulled `origin/main` - repository was already up to date (commit a1bb46a).
- Scanned all tracked files for Cyrillic/Russian text using `git grep` across .py, .md, .txt, .json, .yaml, .toml, .html, .sh, .spec, Dockerfile - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via uv).
- Confirmed repository translation status remains complete; no new changes to translate.

## Completed In This Round (April 10, 2026 - Round 3)

- Pulled `origin/main` - repository was already up to date (commit bfe355a).
- Scanned all tracked files for Cyrillic/Russian text using `git grep` across .py, .md, .txt, .json, .yaml, .toml, .html, .sh, .spec, Dockerfile - zero non-English text found.
- Verified all 29 tests pass successfully (pytest on Python 3.10 via uv).
- Confirmed repository translation status remains complete; no new changes to translate.

## Completed In This Round (April 9, 2026 - Round 2)

- Pulled `origin/main` - repository was already up to date.
- Performed comprehensive scan for Cyrillic/Russian text across all file types (.py, .md, .txt, .json, .yaml, .toml, .html, .sh, .spec, Dockerfile, config files) - zero untranslated text found.
- Verified all source code, documentation, configuration, and templates are fully English.
- Confirmed repository translation status remains complete.

## Completed In This Round (April 9, 2026 - Round 1)

- Pulled `origin/main` and confirmed the local `main` branch was already up to date with no new commits.
- Scanned all tracked files for non-English content using `git grep` with Cyrillic, Han, and Hangul patterns - confirmed zero non-English text remains.
- Verified all 29 tests pass successfully, including:
  - App lifespan and authentication flows
  - CPA upload URL normalization
  - DuckMail service integration
  - Payment link generation with English headers
  - Registration engine with Sentinel POW support
  - Static asset versioning and English locale usage
- Confirmed repository is fully translated and in good working state.

## Next Actions

- Continue polishing wording consistency in comments, log messages, and low-traffic routes as new gaps are found (remaining ~70 comment spacing issues in JS files).
- Expand route-level API coverage for translated payment and account-management actions that depend on backend data.
- Add focused tests for the settings save flows and error messages returned by low-traffic API endpoints.
- Add API tests for access-control edge cases such as malformed cookies and custom logout `next` targets.
- Verify Docker environment variable examples against the actual `settings` names used by the app.
- Authenticate `gh` in a future round if issue and PR inspection is required, since GitHub GraphQL access is currently unavailable in this environment.
