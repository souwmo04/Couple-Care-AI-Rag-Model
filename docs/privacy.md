# Privacy design

## Defaults

- Backend binds to `127.0.0.1`; configuration refuses non-loopback hosts and non-loopback model URLs.
- **Conversation persistence is off.** Conversations live in backend memory (6-hour inactivity
  expiry, 200-conversation cap) and vanish on restart.
- No analytics, trackers, CDNs or remote fonts. `index.html` sets `referrer: no-referrer`.
- Logs are JSON; fields that could hold message text (`query`, `prompt`, `user_message`, …) are
  redacted unless `COUPLECARE_LOG_MESSAGE_CONTENT=true`. Validation errors never echo input.
- Conversations are never ingested into the knowledge base (tested).

## What is stored where

| Data | Location | When |
|---|---|---|
| UI preferences | browser `localStorage` (`couplecare.prefs`) | always, unless guest mode (then `sessionStorage`) |
| Browser client id | `localStorage` / `sessionStorage` in guest mode | always |
| Conversations | `data/user/conversations.sqlite3` | only with persistence enabled |
| Runtime settings | `data/user/settings.json` | after a settings change (no message content) |
| Evaluation outputs | `artifacts/evaluation_results/` | only when an operator runs the evaluation |

`data/user/`, indexes, models and evaluation results are git-ignored.

## Access control

Each browser sends a random `X-Client-Id`; the backend stores only its SHA-256-derived owner key.
Every conversation read, write or delete filters by both conversation id (128-bit random) and
owner, using parameterized SQL.

## Deletion

Delete one conversation, delete all (with explicit confirmation; also clears the on-disk
database even after persistence was turned off, then `VACUUM`s it), clear preferences, or delete
`data/user/`. Guest mode avoids persistent storage beyond the guest flag itself.

## Limits

Local processing reduces transmission, but does not protect against malware, a compromised OS,
shared accounts, or physical access. SQLite files are not encrypted at rest. Browser storage is
readable by anyone with access to the browser profile.
