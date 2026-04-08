# TODO

## Completed In This Round

- Pulled `origin/main` and confirmed the local `main` branch was already up to date.
- Re-checked tracked files for remaining non-English content with `git grep` and confirmed there is no Cyrillic or Han text left in source-controlled files.
- Rewrote the most awkward registration-flow runtime messages and docstrings in `src/core/register.py` so the logs are plain English during signup, relogin, and token exchange.
- Cleaned up remaining machine-translated API field descriptions and comments in `src/web/routes/payment.py`, `src/web/routes/accounts.py`, and `src/web/routes/email.py`.
- Added regression assertions in `tests/test_registration_engine.py` to keep the cleaned registration logs from regressing back to awkward phrasing.
- Verified repository is fully translated: no Cyrillic, Han, or other non-Latin scripts remain in tracked source files, documentation, or configuration.

## Next Actions

- Expand route-level API coverage for translated payment and account-management actions that depend on backend data, not just page rendering.
- Continue reviewing lower-traffic backend modules for awkward English in comments, docstrings, and log output.
- Add focused tests for more user-visible registration and payment error messages after the surrounding API behavior is locked down.
- Run a broader pytest subset in a future round once the full app test dependencies are available in the environment.
- Authenticate `gh` in a future round if issue and PR inspection is required, since GitHub GraphQL access is currently unavailable in this environment.
