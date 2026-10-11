# Luna High final code review — fd20423

Scope: read-only review of the persisted Feishu refresh reservation, strict marker parsing, native Web readiness polling, and focused regression test changes at `fd2042385c4916598337239f5259b3ef1889372a`, compared with `8b6259a9aa6ff2e52b700134abadff24de46dc08`.

## Result

No new P1/P2 finding within the reviewed changes.

- Refresh reservation is persisted through the existing credential store before provider dispatch; a failed write exits before network use. The strict bool field rejects non-boolean stored markers while keeping JSON booleans and the prior missing-field default supported.
- Native startup now requires the matching API run ID and a 200 response from the configured Web URL, serializes readiness probes, and bounds waiting at approximately 30 seconds. Callbacks check timer validity before loading the WebView, so a late result does not override the timeout state.
- The regression test covers malformed marker types and asserts there are no provider calls after detecting corrupt storage.

## Acknowledged migration limitation

Credentials created by an older build have no persisted refresh-consumed marker. If such a build had already dispatched a single-use refresh whose response was lost, `default=False` cannot distinguish that token from a never-used legacy token. The independent 8b report explicitly records this limitation and the compatibility choice; it is not a new or undocumented finding in fd. If the product gate requires protection for previously installed profiles across this upgrade, that policy needs a migration that forces reauthorization for legacy-shaped credentials.

This is a scoped code review only. It does not certify the full Stage B QA matrix or the untested real-service, Keychain, or DMG gates.

当前验收范围补充（收口执行者）：真实OAuth/token次数0、未发布真实adapter、未迁入外部或SWB/SK凭据。旧凭据迁移限制按API契约保留，不用离线PASS覆盖未来的真实迁移验收。
