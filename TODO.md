# TODO

## Completed In This Round

- Pulled `origin/main` and confirmed the local `main` branch was already up to date.
- Re-checked tracked files for remaining non-English content and confirmed the repository is now fully English in source-controlled text files.
- Cleaned up the remaining awkward English comments, docstrings, and startup logs in the FastAPI Web UI entrypoint.
- Fixed the Web UI login flow so the hidden `next` form field is actually honored after authentication.
- Preserved query strings when protected pages redirect unauthenticated users to `/login`.
- Normalized login and logout redirect targets to local app paths only.
- Added route-level regression tests for login failures, auth-cookie creation, authenticated-page redirects, and `next` target normalization.
- Ran the full test suite with `uv run pytest` and confirmed it passes.

## Next Actions

- Continue reviewing lower-traffic backend comments, docstrings, and logs outside `src/web/app.py` for awkward English that does not affect runtime behavior.
- Expand route-level API coverage for translated payment and account-management flows beyond the login gate.
- Decide whether repository-owned generated artifacts such as `tmp_app_core.js` should be normalized, regenerated, or excluded from translation sweeps.
