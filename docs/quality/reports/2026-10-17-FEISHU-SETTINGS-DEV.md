# 飞书高级设置与材料筛选修复

日期：2026-10-17
分支：`codex/feishu-settings-20261017`
产品修复提交：`fe78ba47099f61daf1f4e49f7191eddb9ad544b2`
基线：`e1cb028`（main）
DMG：`.local/internal-builds/fe78ba4-20261017/SummitEverything-Internal-fe78ba4.dmg`
DMG SHA-256：`3deb5ddc113518961e0b3cc2cf463ee29e976deb89a213340dfbcaba20d6c497`

## 现象与根因

1. 真实日历读取连续 `unknown`，后端复现为飞书 404：当前 `identity=app`，
   应用身份没有可用主日历；切到 `identity=user` 后同一范围真实读到 3 条日程。
   设置页原先没有身份 / 日历 ID 输入，用户无法自行修正。
2. 真实材料搜索失败/0 条：该入口只搜索飞书**妙记 Minutes**；真实接口不支持
   `visibility=owner/shared`，但界面仍提供「我拥有的 / 共享给我的」，选中后必然
   `unsupported_capability`。空查询返回 0；真实宽查询「会议」返回 20 条。

## 修改

- 设置 → 高级 → 飞书应用设置新增：
  - 日历读取身份：应用身份 / 用户身份；
  - 日历 ID（可选，留空解析主日历）；
  - 保存时进入 `settingsPatch`，不会被模型设置保存覆盖。
- 真实模式下隐藏「可见范围」筛选，并固定按全部可见读取；
  显示说明「真实飞书只搜索妙记，不支持可见范围筛选」。
- 新增测试：
  - `settingsPatch.test.ts` 断言身份/日历 ID 进入保存载荷；
  - `FeishuPanel.test.tsx` 断言真实模式不渲染可见范围，且材料请求不带
    `visibility`。

## 验证

| 检查 | 结果 |
|---|---|
| Python 全量 | 731 passed |
| Web 全量 | 243 passed / 27 files |
| typecheck / lint / build | exit 0；2 条既有 Oxlint warning |
| DMG | strict codesign、hdiutil verify、packaged smoke 通过；`dirty=false` |
| 真实日历（identity=user，今日范围） | 200，3 条日程 |
| 真实妙记搜索 | 空查询 0 条；查询「会议」20 条 |
| 真实任务读取 | 此前 200，任务列表正常 |

## 当前本机配置

为了完成真实验证，`Test2` profile 的 `feishu.identity` 已切为 `user`，并已保存；
新的设置页现在可以查看和修改。未导入任何飞书材料，只做了只读列表/日历请求。

## 边界

- 飞书任务写回仍禁用；真实妙记只读，不等于云文档/Drive 搜索。
- 已安装 App/公证、五日/双机/发布、完整业务与 WCAG AA 仍 NOT_RUN。
- 本轮真实 OAuth、日历、任务、妙记搜索已用测试库/测试账号范围验证；未把真实
  业务材料写入正式知识。
