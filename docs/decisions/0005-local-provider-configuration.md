# ADR 0005: Local provider configuration and credentials

- Status: Accepted implementation target; the current Stage B candidate implements it only partially
- Date: 2026-10-10
- Context: The current application defaults to Fake providers and an in-memory Feishu credential store. Stage B adds optional remote adapters without making page load, settings changes, preview, or workspace opening trigger network calls.

## Decision

1. Keep provider selection and all non-secret settings in the local profile associated with the active workspace. The workspace directory continues to contain no credentials, index, sessions, or provider secrets.
2. Store provider credentials in macOS Keychain through a single `CredentialStore` boundary. The Keychain item identity includes app namespace, local profile identity, provider, and provider account identity. There is no plaintext-file or in-memory fallback in real mode. Fake mode may use an injected in-memory store for tests only.
3. Keep `fake` as the default mode. Real mode is opt-in and reports capabilities separately from configured state. Settings GET/PATCH and secret status do not contact a provider. A connection test is a distinct, user-triggered action and is a Stage C operation requiring itemized authorization.
4. Never return a secret from an API. Secret entry uses a dedicated, non-echoing form and a dedicated credential endpoint; frontend state is cleared after submission. Error responses contain stable codes and safe messages only.
5. Restrict network destinations to typed providers and known regional endpoint forms. Do not accept arbitrary fetch URLs. Bound request time and response size, disable redirects, parse untrusted responses strictly, and do not retry provider writes.
6. Capabilities whose protocol cannot be proven are disabled individually. In particular, task create/edit/complete remain disabled until all-day date behavior and independent result verification after lost responses are established. Such disabled capabilities do not turn a read-only result into a claim that writes passed.

## Alternatives considered

- Put secrets in profile JSON: rejected because profile contents may be backed up or moved with local files.
- Keep MemoryCredentialStore in real mode: rejected because restarts would lose credentials and it silently fails the persistence requirement.
- Allow arbitrary provider endpoint URLs: rejected because it creates an SSRF surface and makes endpoint identity unclear.
- Retry timed-out writes: rejected because an unknown write may already have taken effect.

## Consequences

- A browser and native development-shell UI share the same authenticated FastAPI settings contract; the FastAPI adapter invokes the OS Keychain through the explicit macOS backend.
- Browser-only or non-macOS real mode reports Keychain unavailable and fails closed.
- Credentials are partitioned per workspace-derived local profile and account. A user must configure each local profile and device independently.
- API, UI, README, configuration contract, and tests must expose the no-network behavior of settings reads and writes.
- Real OAuth, provider connections, material access, model calls, and task writes remain separately authorized operations.

## Evidence and unresolved protocol items

See [Provider Protocol Matrix](../architecture/PROVIDER-PROTOCOL-MATRIX.md), reviewed 2026-10-10. Official sources establish DeepSeek JSON-object output (not a substitute for local validation), Model Studio embedding and rerank request/response shapes, and Feishu user-token use. Current Feishu OAuth refresh details, exact scopes for every selected capability, and Task all-day/result lookup behavior remain under source review. No live request has been made.
