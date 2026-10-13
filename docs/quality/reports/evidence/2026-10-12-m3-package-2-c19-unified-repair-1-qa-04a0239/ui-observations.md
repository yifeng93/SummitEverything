# Browser UI observations

Browser: Google Chrome Incognito. URL: `http://127.0.0.1:15131/`. API: `http://127.0.0.1:18931/`. Only loopback services and synthetic content were used.

1. Created workspace `C19 Isolated QA`, line `QA活动线`, and project `白鹭工程` through the UI.
2. Saved the synthetic source `白鹭工程预算上限为十八万元。赤陶项目活动证章领取须出示邀请函。`, generated a Fake draft, reviewed its body, and explicitly confirmed the formal page.
3. The UI reported one confirmed page, one chunk, and `summit-fake-embedding-v1`; first indexing was manually planned and confirmed.
4. Asked `比较白鹭工程预算与赤陶项目的活动证章领取办法` in `跨材料比较` mode. The displayed completed result had no citations and showed both false gaps: `白鹭工程：缺少预算（活动证章领取）依据。` and `赤陶项目：缺少预算（活动证章领取）依据。`.
5. Reopened the one-question conversation from local history. The same completed body and missing items remained visible.

The UI supplied the request-level check: `POST /api/v1/queries` returned 200, then conversation `/reopen` returned 200. Chrome accessibility-tree observations were captured in the QA session; this CUA interface did not provide an exportable screenshot or DevTools console/network panel, so PNG and browser console/network checks are NOT_RUN. The page's regular query was a local Fake/offline path. This exercise created no tasks and wrote no knowledge after the one explicitly confirmed synthetic page.
