# TODO

## Completed In This Round

- Pulled `origin/main` and confirmed the local `main` branch was already up to date.
- Replaced the last remaining non-English payment-country label from `Türkiye (TRY)` to `Turkey (TRY)`.
- Added a regression test to keep the payment template country list fully English.

## Next Actions

- Continue reviewing low-traffic backend comments, docstrings, and logs for awkward English that does not affect runtime behavior.
- Expand route-level API coverage for translated payment and account-management flows.
- Decide whether repository-owned generated artifacts such as `tmp_app_core.js` should be normalized, regenerated, or excluded from translation sweeps.
