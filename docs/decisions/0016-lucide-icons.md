# ADR 0016：所有图标统一使用 Lucide

日期：2026-10-28。状态：Accepted。只改图标来源与绘制方式，不改导航结构、页面区块或业务行为。

## 背景

侧栏五个导航图标原先是 CSS 手绘几何：今日用方形加横线、审批用边框拼对勾、项目用两个小方块、问答用圆形加斜线、设置用圆环。它们的基准线、视觉重量和内部留白都不一致，缩小到 18px 后明显错位；其它位置的「文 / 记 / 想 / 知 / 待 / 答 / 提」以及 `← ＋ ↗ › ✕` 也各自是文本符号，字体不同就会跳动。

## 决定

1. 新增运行时依赖 `lucide-react`（纯 JS，无原生绑定）。
2. 侧栏固定映射：今日 `Sun`、审批 `ClipboardCheck`、项目 `FolderKanban`、知识问答 `MessageCircleQuestion`、设置 `Settings`；统一 18px、`strokeWidth=1.75`、`currentColor`。
3. 其它独立图形统一改为 Lucide：
   - 文件/来源 `FileText`；日志 `NotebookPen`；思考/建议 `Lightbulb`；正式页 `BookOpen`；待确认 `Clock`；回答 `Sparkles`。
   - 返回 `ArrowLeft`；新建/追加 `Plus`；引用外开 `ArrowUpRight`；列表进入 `ChevronRight`；折叠 `ChevronDown`；提示关闭 `X`。
4. 尺寸约定：导航 18px；行内标记 14px；动作图标 14–15px；折叠箭头 15–16px；描边统一 1.75（关闭按钮 2）。
5. 以下不算图标，保留原样：品牌字母 `S`、工作库首字头像、状态圆点、数量徽章、引用序号。
6. 禁止再用 Unicode 符号（`← ＋ ↗ › ✕`）或 CSS 拼几何作为图标；需要新图标时从 `lucide-react` 引入。

## 后果

- 导航图标的视觉尺寸与基线由 SVG 统一，不再随字体或手绘边框漂移；移动端底栏同步使用 16px。
- 按钮的可访问名称不再包含 `←` / `＋` 等符号；`App.test` 与 `ProjectsView.test` 中对应的按钮名同步改为纯文字，行为断言不变。
- 图标随用随引，Vite 只打包实际使用的图标；无新增构建步骤或原生依赖。

关联规格：[前端指南](../product/FRONTEND-GUIDE.md)、[逐页规格](../product/FRONTEND-PAGE-SPECS.md) §9。
