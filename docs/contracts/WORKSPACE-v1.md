# 工作库契约 v1

状态：Accepted engineering baseline，2026-10-09。本契约实现产品规格；当前 Python 骨架只覆盖 §4 的部分，完整读写由 M1 实现。

## 1. 库与身份

新库以 .summit-everything/manifest.json 和 conventions.md 识别。manifest 包含 version: 1、workspace_id（UUID）、name、created_at（有时区的 ISO 时间）及线 / 项目注册表。

线记录：id、name、directory（相对库根目录）。项目记录：id、line_id、name、directory、overview_id、archived。ID 用 UUID，改名不换 ID；路径只作定位。

创建新库使用用户选定的新目录；发现 legacy manifest、已有未知内容或旧 _vault 时不静默转换。既有资料由明确入库操作处理。

目录示例：

~~~text
工作库/
  conventions.md
  行政&后勤/
    场地与酒店/
      项目总览.md
      示例对象.md
      示例案例.md
  工作日志/                 # 不绑项目的记录
  工作思考/
  原件/                     # 只作来源，永不检索
  .summit-everything/
    manifest.json
    intake/                 # 待处理当前状态
    drafts/                 # 待审正文
    actions/                # 待执行 / unknown 外部动作
    transactions/           # 未完成本地写操作
    sources/YYYY-MM.json    # 来源目录、hash、来源标识
    history/YYYY-MM.json    # 完成流程与结果汇总
~~~

这不是固定项目集合。项目内不强制类型子目录；页面标题可读，重名生成明确不覆盖的文件名。conventions.md 是本契约的人类可读说明，不是自由执行的脚本。

每条待处理项以 `state` 表达来源到整理作业 / 稿件的当前关系：`pending`（尚未整理）、`processing`（整理作业进行中）、`reviewing`（已有待审核稿）、`completed`（关联稿件均已确认）、`failed`（整理失败）、`cancelled`（用户取消）。`latest_job_id` 指向最近一次显式整理。只有 `pending` 可直接整理；完成、失败或取消的来源需要明确的重新整理动作，处理中或待审核来源始终拒绝重复生成。旧库没有 `latest_job_id` 时由作业记录恢复状态。

## 2. 页面元数据与正文

正式页使用 YAML frontmatter。最少 id、title、role: knowledge、kind；普通页和项目总览需要 line_id、project_id。log / thought 可以不绑定，也可以只关联线。其他项目用 related_project_ids 或正文链接引用，不能新增第二个平等主归属。

kind 的值与 UI 名称：

| 值 | 名称 |
|---|---|
| project_overview | 项目总览 |
| object | 对象档案 |
| case | 案例 |
| topic | 主题知识 |
| decision | 业务决策 |
| log | 工作日志 |
| thought | 工作思考 |

可选业务字段：summary、tags、aliases、date、created_at、updated_at、business_status、source_refs、related_project_ids、superseded_by。业务标签自由。日期以 ISO 字符串写入；解析器把 YAML date / datetime 转成 ISO 字符串。

validity 为 current（默认）、superseded、invalid，表达知识效力；业务完成或项目归档不自动修改它。business_status 不强制枚举，按业务需要填写；模型不能通过它改变项目进度。

正文没有固定区块要求，允许任意合理 Markdown。重要事实只在权威页完整维护，其他页用相对 Markdown 链接或带出处摘要。优先使用可移植的相对链接；遇到不能唯一解析的旧 wikilink 不猜测目标。

API / reader 验证 UUID、字段类型、所属项目存在、物理目录与归属一致、保留目录、重复 ID 和路径逃逸。未知 JSON-compatible 元数据保留，不静默删除。可信资格模块不是这些完整验证的替代品。

## 3. 原件与稿件

导入原件保存原始字节和 SHA-256；粘贴文字也形成来源记录。机器来源目录记录 role: source，UI 标识“原件 / 不进入检索”；不为了标记而篡改原文件字节。

用户选择冲突依据或标记未决后，正式正文也记录该结果；未决结果明确写为尚未确定事实。原件与待审稿不会因状态变化而删除。

原件目录和 system / draft 存储区是硬排除层；任何正文、frontmatter、模型输出或伪造 approval 都不能覆盖路径判定。其他位置明确 role: source 的页面也排除。

稿件包含 draft_id、input_ids、target_page_id（新增时为空）、metadata、body、expected_base_sha256、重要冲突及处理结果、独立 action 建议。一份输入可以关联多稿，每稿独立确认。

AI 只生成稿件与建议，不生成批准证明、不执行动作。用户编辑稿件的全部变化都进入最终版本。显式记为未决可以确认，不能把未决写成已解决。

## 4. 当前版本批准

approval 结构：

~~~json
{
  "version": 1,
  "content_sha256": "64位小写SHA-256",
  "confirmed_at": "2026-10-09T04:00:00+00:00",
  "confirmation_id": "稳定的用户确认意图ID"
}
~~~

confirmation_id 在同一次确认的重试间不变。confirmed_at 必须有时区。证明由用户显式确认的应用写路径生成；不是模型输出，也不是签名或防恶意篡改认证。

canonical 内容为 JSON 对象 {metadata, body}：metadata 包含解析后的所有 frontmatter 字段，唯独排除 approval；不加入解析器默认键。body 将 CRLF / CR 转为 LF，保留其余空白。拒绝正式正文 BOM。JSON 用 UTF-8、ensure_ascii=false、sort_keys=true、separators=(',', ':'), allow_nan=false，计算 SHA-256。

文件位置不进入 hash；标题、归属、来源、知识效力和未知元数据的变化都进入 hash。不能把旧证明复制到新正文。更改算法或 normalization 需要契约版本与迁移方案，不静默重新批准。

基准 API：

~~~python
content_sha256(metadata, body) -> str
retrieval_eligibility(
    metadata, body,
    area=StorageArea.FORMAL,
    purpose=RetrievalPurpose.CURRENT,
    expected_content_sha256=None,
) -> Eligibility
~~~

StorageArea 必须由真实 reader 按路径与记录分类，不能来自前端或模型声明。普通内容先完成完整 schema / 归属验证，再调用资格函数。

索引以 HISTORY 检查所有当前已批准版本，保留效力标记。普通问答以 CURRENT 检查；仅明确历史范围可使用 superseded / invalid，回答必须说明其效力。

**查询最终候选、邻页与引用必须重读当前文件，并把缓存版本传入 expected_content_sha256。** 新内容重新批准也不能证明旧缓存片段有效。失效资格、版本不匹配或无法读取时移除该候选；不得仅相信 SQLite 中的 approved 列。

## 5. 保存、并发与恢复

本地修改必须携带稳定 operation_id、request hash 和预期内容版本。新页的基准为空，更新页的基准为已读取 hash。基准变化返回冲突，不覆盖。

同库 UUID 的本地锁覆盖检查、意图认领和写入，避免同机并发请求先检查后执行。意图先记录，再写临时文件与 replace，最后记录结果；恢复同一意图，不能因超时生成新 ID。

多文件修改使用可恢复 journal，记录全部变更路径、目标版本和阶段；每次读取 / 启动先处理相关未完成事务。未经确认的稿件不会因恢复变为正式页。

外部移动同项目页面可更新路径索引；跨项目移动或归属不一致进入结构待确认。显式应用重命名 / 移动维护链接与注册表；仅对原本批准有效、且目标页面身份未变的确定性结构改写，可用该用户操作更新证明。待审或失效页不得顺便自动批准。

线 / 项目名称冲突或路径逃逸拒绝。非空线先迁移项目再删除；非空项目用归档，硬删除只允许空项目。不级联删除知识、来源和未决操作。

## 6. 外部动作与幂等

action_id 表示意图，不是尝试。保存 payload_sha256、确认、状态和 provider 结果，再发外部请求。相同 ID / 相同 payload 重放结果或返回进行中；同 ID / 不同 payload 拒绝。

外部状态：proposed、confirmed、running、succeeded、failed、unknown。超时 / 进程退出不能证明远端没执行；unknown 只读核实或由用户提供明确结果后解锁，不能自动重 POST，也不能靠任务同名推断成功。

完成 receipt 保存在可迁移月汇总中，建立本地查找缓存。unknown / running 未决结果不压掉；去重记录不使用随意 TTL。新意图可有同样正文，不能按标题误合并合法的两项任务。

项目进度变更也是独立确认 action，走本地事务；知识批准不隐式执行该 action。

## 7. 本地状态与同步

profile 保存 workspace_id 对应的本机路径配置、SQLite、向量、历史、角色、记忆、缓存及日志，长期凭据在钥匙串。工作库没有本机绝对路径、秘密或运行中 SQLite。

每个待处理流程只保留当前业务状态，完成后按月归档，诊断事件只写本地轮转日志。同步状态与来源 / 幂等证据不能混称“垃圾日志”直接删除。

OneDrive 客户端负责同步。应用报告“已保存到本机”，不报告未经确认的云端完成。换机先停写并确认客户端同步，再启动另一写端；重复 ID、冲突副本和未完成事务阻止相关写入，不实现云端锁或自动合并。

另一机可查看待审稿；中断模型 job 的未知调用不得后台重发。索引首次建立在每台机器单独显式确认，不能误称为仅增量免费同步。

## 8. 样板特殊入口

「场地与酒店」通过后续一次性业务 grillme 确认。只有最终确认页经正式写路径初始化，不把四份待审来源文件复制到新库；原桌面文件保留。

这不改变普通导入保留原件的规则，也不允许测试 agent 自动写真实样板或把真实样板提交到测试 fixtures。


## M2.2 回执实际落盘补充

`.summit-everything/action_receipts/active/<action UUID>.json` 保存 exact payload / SHA-256、kind、候选 / 来源关联、确认及时间、attempt_session、状态、安全 provider_result 与 evidence。完成后的旧月份进入 `completed/YYYY-MM/summary.json`，schema=`action-receipt-month-v1`、items 按 UUID；先原子 replace 汇总，再删 active，删除中断造成的完全相同副本允许，冲突副本 / 内容 hash 损坏阻止写。当前按真实 receipt 扫描查找，未另加可失效的索引缓存。

proposed / confirmed / running / unknown 无 TTL；仅 succeeded / failed 且 finished_at 属旧月份的记录归月。新进程看到另一 attempt_session 的 running 原子改 unknown，不重发。每次 receipt 认领 / 修改使用同库身份锁；网络期间不持库锁。未知可只读核实，终态 / 人工依据保留，迟到返回不能覆盖已明确终态。

ProjectRecord 追加可兼容默认字段 progress（空文本）、progress_version（0）、progress_confirmation_id（null）。独立 project_progress 将预期版本与确认一起写既有 manifest writer transaction；中断恢复可读 write_intent 的 request_hash / operation_id 与磁盘结果核对，不重新应用业务进度。知识正文和进度不共享确认。

旧 `.summit-everything/actions` 候选保留不改；用户审阅转换后，新 receipt 记录 candidate_id、source_draft_id、source_ids。候选文本不解释为可执行命令或批准。Fake 的 `simulated_remote_tasks.json` 在产品库 / profile 之外的临时模拟目录，包含合成 task 事实及执行结果证据；工作库 receipt 的任务投影只说明执行当时返回，不是第二套任务数据库。
