# M3 包 2 C19 统一 repair 2/2 独立 QA

日期：2026-10-12。最终结论：**FAIL（P1）**。这是该统一 C19 修复周期 repair 2/2 的 fresh QA；QA 仅记录证据，不修改产品实现、tracked tests 或配置。Sol 决定 C19、包 2与 M3 总门。

## 固定版本与边界

受测固定 QA HEAD 为 `262f4eaa418d70f983f3b0b260d3635cd2e28c92`；其中产品源码树固定为 `f79f613a902758da3173a5b27219fa568a912f5e`，HEAD 相对源码仅含7项交接文档。初始 checkout clean。自动化及浏览器使用 Fake/offline provider、loopback、隔离 profile 和合成工作库。未触碰 `src`、`web`、`native`、已有 tracked tests、依赖、锁文件或配置；最终产品树 diff 检查 exit 0。测试期间固定 HEAD 未变化。API/Web 开发服务停止后两个监听端口均无 listener。

repair 1/2 QA 的历史 P1 FAIL和更早候选失败均保持有效。旧 harness 中 `test_fresh_same_page_multiple_objects_do_not_cross_pair_dimensions` 第132行要求赤陶主题仍 missing，但该 fixture 已包含对应的正式证章正文；本轮只在 QA 副本更正为 complete positive，并增加删除赤陶正文的 partial 对照。旧QA源 harness、旧报告与旧 hash/evidence均未改动。更正依据、独立副本和 hash 证据见[本轮 evidence](evidence/2026-10-12-m3-package-2-c19-unified-repair-2-qa-262f4ea/README.md)。

## P1：未知 exact 主题中的“设备”被剥除，丢失现有证据

**最小材料。** 两个经确认的 synthetic 页面：白鹭/枫湾项目正文含预算上限；赤陶/玄石项目正文原样含 `访客设备领用须登记姓名并归还胸牌`。问题分别为“比较枫湾活动预算与玄石展览的访客设备领用办法”与对象换序的等价问法。

**预期。** 范围计划为 `(枫湾活动, budget)` 与 `(玄石展览, term:访客设备领用)`。完整语料应引用两个 pair，provider passages 应包含两段支持正文且 missing 为空；对同一对象单独询问该 exact 主题也应能引用。三模式都应保持相同范围。

**实际。** planner 输出 pair `(玄石展览, term:访客领用)`，把问题中的“设备”删除；正文的真实支持段含“访客设备领用”，`supported_dimensions` 因此不匹配。Fact/comparison/plan与反序均只引用预算，把答案标为 partial 并虚报玄石“缺少term:访客领用依据”；answer provider 被调用1次，但只收到预算 passage。只问“玄石展览的访客设备领用办法是什么？”时零 citation、missing 仍错误且 provider 0次。可复演命令：

~~~sh
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src:.local/qa/c19-r2/harness" uv run python .local/qa/c19-r2/harness/reproduce_device_topic.py
~~~

实际 plan、citations、provider passages/count、missing 与 body 均在 `evidence/2026-10-12-m3-package-2-c19-unified-repair-2-qa-262f4ea/raw-logs/device-topic-reproduction.jsonl`。另一个9项 holdout 的完整混合支持用正确主题“活动证章领取”验证：3模式均有两条 citation、provider 收到两段、missing 空。故发现针对同范围 pair→支持判定的具体损失，非“所有 exact 主题均不可用”。

严重度为 **P1**：用户提出明确对象和主题且库内已存在对应正式知识时，产品漏引用并错误宣称资料缺失。限量结构矩阵总计15 PASS、7 FAIL；7项是该同一归一化缺陷的完整、反序及独立主题重现，不作为七个独立缺陷。共用预算/排期四 pair、两个对象各有局部主题的两 pair、同对象多个可匹配 exact topic、两个陌生主题无依据零调用、同chunk不得跨 pair、alias/title/名字含 budget/time 不应污染等相关场景通过。

## 检查与浏览器结果

安装 `npm --prefix web ci` 与 `uv sync --locked --group dev` 均 PASS。原 repair-1 12项 holdout副本12/12 PASS；修正错误赤陶 missing 预期并独立增加 partial 的9项副本9/9 PASS。README适用完整检查：guarded pytest **450 passed**；Web **56 tests / 12 files**；Ruff check/format、mypy 43源文件、lock check、`uv build`、Web typecheck/lint/build 全部退出0。隔离执行 `app.openapi()`/Citation、Answer schema导出与 `openapi-typescript`，仅写 `.local/qa`，和tracked `generated.ts` diff无差异。唯一既有警告为一条 Starlette/httpx deprecation；其余输出见逐条原始日志。

Chrome loopback WebUI通过可访问树真实观察了创建隔离库、合成知识确认、Fake首次索引、跨页问答和历史重开。mixed family+exact device query在真实UI重现只引预算且缺第二 pair，点击历史重新打开后相同错误仍在；`预算+登记姓名`完整控制显示两个当前有效来源；活动餐券登记真缺失时只显示预算部分来源与对应缺口；陌生 exact主题无资料时显示零引用和缺失。`POST /api/v1/queries`与conversation `/reopen`均返回200；业务正确性以呈现材料为准。DevTools console/network与PNG未由当前工具接口实际取得，**NOT_RUN**。观察详情与服务请求日志见evidence。

## 门状态与限制

| 门 | 结果 |
|---|---|
| C19 固定 SHA 离线结构/行为 | **FAIL（P1）** |
| repair-1旧holdout 12项 | **PASS 12/12** |
| 修正后repair-1新增holdout 9项 | **PASS 9/9** |
| 扩展有限矩阵 | **FAIL 7 / PASS 15**，7项为同根因 |
| README自动后端/Web/静态/构建检查 | **PASS** |
| OpenAPI→TypeScript隔离稳定性 | **PASS** |
| Browser mixed device exact case | **FAIL**；历史重开保持失败结果 |
| Browser usable exact/full control, actual partial, unknown-zero | **PASS** |
| DevTools console/network/PNG | **NOT_RUN** |
| 真实服务/provider、材料、凭据、Keychain、runtime暴露 | **NOT_RUN / UNVERIFIED** |
| native、DMG、五日、双机、release | **NOT_RUN** |
| smoke | **0次** |
| C13/C14/C20/C21及包1/包3 | 未重开全流程；源码树相同且本轮全量后端/Web回归通过，既有独立QA结果沿用既有报告范围 |

C19 P1未通过，因此本QA不能建议包2或M3通过。下一步由Sol处理最终repair失败并向产品负责人报告；QA本身不启动第三轮修复。重要里程碑merge、真实外部验收与发布均未执行。
