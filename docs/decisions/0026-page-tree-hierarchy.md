# ADR 0026：页面目录改为真实文件夹树

日期：2026-10-29。状态：Accepted。用户指出项目页左侧只显示两个层级，遇到 `docs/user/develop/basic` 这类多层目录时会把 `basic` 和 `subsystems` 排成平级，属于错误。此 ADR 只改目录的构建与展示，不改页面数据、路径规则或确认门。

## 背景

`page-groups.ts` 原来按 `source_path` 的**最后一段目录**分组：`docs/user/develop/basic/intro.md` 和 `docs/subsystems/slots.md` 会得到 `basic` 与 `子系统` 两个平级分类，中间层级全部丢失。真实语料里 `docs/user/develop/` 下还有 `basic`、`framework`、`practice` 三层，压平后既看不出归属，也无法按文件夹浏览。

## 决定

1. **按完整路径建树**：目录节点 = `source_path` 的每一段目录，节点保留直接页面与子节点，计数为子树页数。
2. **单一文档根上提**：只有一个根（导入通常是 `docs/`）时，把它的子目录提到顶层；根自己的页面单独成「总览」。多根时按根展示，不合并不同来源。
3. **项目页**：左栏是可展开/收起的文件夹树（节点计数 = 子树页数），右栏是选中节点的子树页面；深层页面在行内标注相对子目录（如 `develop / basic`）。
4. **阅读页**：左目录同样按树渲染，当前页所在路径默认展开；面包屑逐层写全（`官方文档 / 使用 / develop / basic`）。
5. **无来源页面**：没有 `source_path` 的页面进「其他页面」节点，不与文件夹混排。
6. **翻页**：正文尾部「上一篇 / 下一篇」取当前文件夹的直接页面，按 `relative_path` 排序；换页回到正文顶部。

## 后果

- `page-groups.ts` 从「分组函数」改为「建树 + 路径查询」：`buildPageTree`、`subtreePages`、`findPageTrail`、`findNodeByKey`、`relativeDirLabel`。
- 项目页与阅读页共用同一棵树，不会再出现同一页面在两处归属不同。
- 项目页树宽 200px，四层缩进后页面标题仍可见；更深的层级靠省略号截断，不换行。
- `ui-contract.allowlist.json` 更新 `PageReader` / `PageTree` 计数，新增 `page-groups.ts:page_id` 一条。
- 新增 `page-groups.test.ts` 覆盖：多层不被压平、子树页面与面包屑、无来源页面单独成组。

关联规格：[逐页规格 §5/§6](../product/FRONTEND-PAGE-SPECS.md)、[ADR 0022](0022-reading-directory-and-page-actions.md)。
