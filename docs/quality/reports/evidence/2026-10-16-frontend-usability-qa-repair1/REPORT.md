# Frontend usability repair 1 — 独立 QA 报告

- 被测 SHA：`d9f49c1fc1b2dc787b21e3f2bd47662de3d1e715`（开始及结束均核对）。
- Checkout：`/Users/yifengstudio/.codex/worktrees/frontend-usability-qa-repair1/SummitEverything`。
- 范围：本轮ApprovalView异步刷新/目标身份修复，以及交接指定离线UI和批次确认路径。所有业务输入为合成内容；本地Fake服务；浏览器外联拦截。
- 结论：本次固定SHA上已执行的本地自动检查与核心离线复演均PASS。Sol仍须作最终阶段门判断；未执行的外部/安装门不由本报告推断。

## 结果

- `npm ci`：PASS，226 packages，0 vulnerabilities；原始记录见 `logs/npm-ci.log`。
- `npm test`：PASS，239/239；`npm run typecheck`：PASS；`npm run lint`：PASS，保留既存 App.tsx 与 ProjectsView.tsx 各一条 warning；ApprovalView 无 lint warning。`npm run build`：PASS，Vite报告主 JS chunk 603.32 kB 并给出 >500 kB advisory。`npm run api:types`：PASS。原始日志均在 `logs/`。
- `npm run test:e2e`：首次真实退出码 1：first-use通过，viewport场景在browserContext.close时报Playwright trace/zip artifact `ENOENT`；未能从日志确认根因。相同命令重跑退出码 0，2/2通过。首次与重跑日志分别保留为 `logs/web-e2e.log`、`logs/web-e2e-final.log`。`npm run test:e2e:integration`：PASS，1/1 本地 FastAPI/Fake。
- 独立延迟响应 harness：当前SHA 5/5 PASS，覆盖刷新epoch旧响应不能覆盖新目标、旧详情不能覆盖新来源、已消费目标后仍pending的详情正常完成、数据未就绪不提前消费target、unmount后延迟响应安全。旧行为 `0957df2` baseline 的同一harness有两项预期失败（旧refresh覆盖新target、旧详情覆盖新来源），其余三项通过，形成反例。日志分别为 `logs/async-harness-current.log` 与 `logs/async-harness-baseline-0957df2.log`；baseline源码仅从git archive复制至隔离 `.local/qa`。
- 离线浏览器响应式场景：320/390/768/960/1024/1280/1440宽度、明暗主题下的今日/审批/工具抽屉/设置均检查页面及body横向scrollWidth，脚本断言无页面级横向溢出；1280×800今日页有非空会议与待办，默认3/5、展开全部、首行以及capture/import入口均已复演。Playwright还检查了文件选择入口和对话框关闭后的焦点、dirty编辑取消后保留、接受离开再返回焦点、Markdown标题渲染。键盘/焦点为这些具体路径的实测，不代表整站完整键盘审计。脚本、manifest、截图在 `harness/viewport-qa.spec.ts`、`evidence/viewport-independent/`。
- 颜色对比：运行时采样了1280宽今日与审批的代表性标题、说明、计数和按钮文字；本次采样最小比值为浅色4.72:1、深色6.97:1，均达到普通文字4.5:1阈值。该采样范围有限，整站、所有状态及非文字图形的WCAG AA审计为NOT_RUN；不能从响应式通过推断整体AA。
- focused browser合成场景PASS：同名来源使用精确ID、Markdown、dirty取消保护/焦点返回；已确认page且store.pages为空时索引提醒仍可见；未触发动作/外部模型/索引写入。原始manifest与截图见 `evidence/focused/`。
- 批次文件导入mock PASS：分别注入201/400/503；只选择成功ID；失败需用户显式retry后第二次成功；未知503仅请求一次；未选择失败/未知项。浏览器pageerror=0、外联尝试=0。控制台四条资源失败信息对应脚本故意注入的400/503响应，属于预期注入。见 `evidence/batch/file-batch-mock-manifest.json`、`logs/file-batch-mock.log`。
- FastAPI/Fake多稿场景PASS：一个合成来源拆出两份稿，显式确认一稿后另一稿仍pending；仅产生一页正式内容；无动作候选、任务写入或项目进度修改。启动初期GET返回workspace 409及first-use 404是空工作库初始化预期；pageerror/consoleErrors/外联尝试均为空。见 `evidence/multidraft-2997/manifest.json` 与截图。

## 代码质量与状态

对 `b32df36..d9f49c1` 的diff检查确认只改 `ApprovalView.tsx` 与其测试；移除了两处 `oxlint-disable-next-line`，未发现替代 suppression、规则配置弱化、依赖/lock变更或删除测试。新增测试4项；本地整套web单测239/239。`git diff --check`通过。`npm ci`、OpenAPI类型生成后无tracked文件改动。

独立 QA 工作树结束时 `HEAD`仍为上述SHA，tracked工作树clean。所有本轮脚本、日志和截图留在忽略的 `.local/qa/frontend-usability-d9f49c1/`。

## 未测项与风险

- NOT_RUN：真实服务/凭据/用户Keychain/外部模型/飞书、真实业务材料、已安装应用、公证与DMG实际安装验收、五日及双机观察；没有调用真实外部服务。
- NOT_RUN：项目、知识、问答等未在本轮核心交接要求内复演的完整页面行为；整站键盘和完整WCAG AA审计。
- 模型runtime metadata本轮未实际暴露，状态为UNVERIFIED；不根据配置文件推断。
- `items.filter`端点fixture按要求提供 `{items,next_cursor}`，未将初验早期fixture问题记为产品缺陷。
- 2条既存lint warning及603.32 kB bundle advisory仅为告警，本次命令均退出0。

详细原始命令退出码见 `check-status.json`；截图及raw日志在本目录的 `evidence/` 与 `logs/`。
