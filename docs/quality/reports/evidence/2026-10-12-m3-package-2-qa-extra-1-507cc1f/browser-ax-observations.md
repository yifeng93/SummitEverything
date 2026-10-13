# Browser accessibility observations (synthetic workspace)

- PageReader for approved superseded history: heading/state `已确认 · 已被替代`; visible notice says this page is superseded, for historical reference only, and not current Q&A evidence.
- After externally changing the synthetic page body/hash: state `待确认 · 已被替代`; visible notice asks to inspect and confirm the current body before the new version regains retrieval eligibility.
- After clicking the explicit confirmation action: state `已确认 · 已被替代`; historical-only notice remains. The current index updates, but page validity does not change.
- PageReader for approved invalid history: `已确认 · 已失效`; visible notice says invalid history is for historical reference only. The PageWriter explicit reconfirm operation keeps `validity=invalid`.
- A previous citation for an externally changed hash displays as unavailable and does not silently open the changed body. Direct request using the old expected hash returns HTTP 409.
- Memory flow: attested user-authored preference creates a pending candidate; editing still requires the separate “确认并保存” action. After confirmation it is shown as active and is included in the subsequent provider request.

Browser checks used generated workspace content only. DevTools console/network panels were not exposed by the available browser automation and are NOT_RUN.
