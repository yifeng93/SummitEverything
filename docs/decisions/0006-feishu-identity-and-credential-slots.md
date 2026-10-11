# ADR 0006: Feishu identity preference and credential slots

- Status: Accepted; implemented in the Stage B candidate (`codex/deepseek-stage-b-trial`)
- Date: 2026-10-10
- Context: The user decided that Feishu connection must not require an OAuth login for every
  capability. Official documentation shows that some endpoints accept either
  `tenant_access_token` or `user_access_token`, while minutes search and task list accept
  only `user_access_token`. The previous candidate had a standalone Feishu token store
  whose Keychain slot scheme did not match the settings credential vault, so the app secret
  and user token could live in two disconnected places.

## Decision

1. Prefer application (tenant) identity wherever the documented endpoint accepts it. The
   HTTP adapter resolves a tenant token from the app secret for calendar, transcript and
   artifact reads and for task read/create/edit.
2. Require the one-time user authorization only for the endpoints that document
   `user_access_token` as required: minutes search and task list. Renew automatically via
   `refresh_token`; when renewal fails, disable only the affected capability and show a
   re-authorization prompt.
3. Keep one credential slot system. The Feishu app secret occupies the same
   `feishu_app:<account hash>` vault slot that the settings UI writes; user tokens occupy
   `feishu_user:<account hash>` in the same profile namespace. The account identity for both
   is the Feishu app ID, so a different app or profile cannot read another identity's
   tokens.
4. Keep capabilities whose semantics are unproven disabled individually. Task
   create/edit/complete stay disabled because no documented endpoint can prove a write by
   `client_token` after a lost response.
5. Keep as default that real provider business reads and model calls are refused
   server-side; the adapter is reachable only behind an explicit Stage C authorization flag.
6. Never treat a free-text account label as a verified Feishu identity. Only `open_id` from
   the official user-info endpoint would bind an account, and that call is not part of the
   Stage B run.

## Alternatives considered

- Require user OAuth for every Feishu capability: rejected by the user because it makes a
  login a universal precondition and assumes app credentials reach personal resources.
- Fall back to another identity after a permission error: rejected because silently widening
  access is not a user decision.
- Keep the standalone `KeychainCredentialStore` namespace: rejected because the app secret
  and user token would not be visible to each other, producing two unconnected slots.

## Consequences

- `FeishuConfig.identity` selects app-first or user-first; `scope_materials` and
  `scope_calendar` carry the exact documented scope strings in real mode.
- The adapter maps documented error codes to `token_expired`, `missing_scope`,
  `not_found`, `provider_timeout` and `provider_unavailable`, and refuses a
  `visibility` filter that the real search endpoint does not accept.
- Real Feishu data routes return `stage_c_authorization_required` until
  `feishu.real_data_enabled` is set after itemized Stage C authorization.
- `KeychainCredentialStore` remains as an offline contract but delegates to the shared
  vault so there is still exactly one slot scheme.

## Evidence and unresolved protocol items

See [Provider Protocol Matrix](../architecture/PROVIDER-PROTOCOL-MATRIX.md), reviewed
2026-10-10 against the official Markdown endpoints. OAuth authorize, token exchange,
refresh rotation, tenant identity, minutes search/transcript/artifacts, calendar events and
task read/create/edit shapes are now quoted from first-party prose. Remaining unknown:
live account scope availability, binary transcript content type, and any endpoint that
would prove a task write by idempotency token. No live request has been made.
