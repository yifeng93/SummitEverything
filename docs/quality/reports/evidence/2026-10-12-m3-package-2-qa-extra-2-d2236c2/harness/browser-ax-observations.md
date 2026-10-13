# Browser accessibility observations — M3 package 2 extra 2

Target: `http://127.0.0.1:15573`, synthetic workspace/profile A. Browser opened through CUA; no real files or account data.

- Asked about Qinglan's superseded budget with `包含历史版本` selected. The historical citation opened the page reader, which displayed `已确认 · 已被替代` and said it was historical-only, not a current answer basis.
- Asked the same topic with the current range selected. The answer did not cite the superseded page.
- Asked for the expired Jichuan budget with history selected. The citation opened a page reader displaying `已确认 · 已失效` and historical-only guidance.
- After editing Qinglan's approved page body externally (synthetic 18 万元 → 21 万元), the directory marked it `待确认`; the older citation displayed `原引用已不可用 · 引用版本仍可用`. Opening the page from the directory showed `待确认` and explained the content no longer matched its confirmation. The old citation did not open as a usable source.
- Entered `我偏好用简短中文回答，并明确标出资料没有提供的数字`, checked the user's own-expression attestation, and created a pending memory candidate. The candidate remained pending until a separate confirmation action; after confirmation it appeared as an active memory. Provider payload behavior was independently checked through a local fake transport.

The browser accessibility surface exposed these rendered states. DevTools console/network panels were not exposed in this run (NOT_RUN).
