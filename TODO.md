# TODO

## Completed In This Round

- Pulled `origin/main` and confirmed the local `main` branch was already up to date.
- Replaced the remaining hard-coded payment checkout locale header from `zh-CN` to `en-US`.
- Added regression tests for Plus and Team payment link generation so the checkout request headers stay English.
- Fixed the stale absolute README link to `docker-compose.yml` so it points at this repository workspace.
- Replaced the remaining frontend display locales from `zh-CN` to `en-US` for timestamps, date formatting, and number formatting.
- Added a regression test that checks the shipped frontend assets keep English locale formatting.

## Next Actions

- Continue reviewing low-traffic backend comments, docstrings, and logs for awkward English that does not affect runtime behavior.
- Expand route-level API coverage for translated payment and account-management flows.
- Verify Docker and environment-variable documentation against the actual settings names used at runtime.
