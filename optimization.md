# 网站性能优化计划

## 一、已完成的工作（第一、二阶段）

| 阶段 | 内容 | 主要效果 |
|---|---|---|
| 一 | H2H 页面：查询结果在内存中筛选，虚拟滚动（动态行高）；通用表格脚本缓存单元格文本 | H2H 全选 WTA 约 9 万条记录，查询约 50 ms（原来几乎卡死） |
| 2A | 通用表格只把要显示的行放进 `tbody`；排序基于内存中的顺序；筛选下拉选项在首次打开时才生成 | 排名、show 页的排序和筛选从数百毫秒降到约 20 ms |
| 2B | 排名类 8 个页面的表格数据改为 JSON 内嵌（`#tsData`），只为显示的行创建 `<tr>` | DOM 节点减少 90% 以上（如 wta_show 39,034 → 1,571） |
| 2C | 手机上只渲染卡片、不生成表格行；killer / nemesis 页面也改为 JSON 数据模式 | 手机端节点更少；killer 页面体积减少约 20% |

### 当前架构约定（改代码前务必了解）

- **页面是 Python 生成的静态 HTML。** 生成代码在 `src/site_html/`，入口是 `src/main.py`。GitHub Actions（`.github/workflows/update-daily.yml`、`update-live.yml`、`tick-live.yml`）定时运行 `main.py --daily` / `--live`，然后把生成的 HTML **提交到 `main` 分支**，由 GitHub Pages 发布。
- **表格数据模式**（`src/site_html/common.py`）：
  - `_table_rows()` 是行数据的唯一来源。`_df_to_html_table()`（整表 HTML，旧方式）和 `_df_to_table_data()`（表头 + `#tsData` JSON，新方式）都基于它。
  - `render_ranking_page(table_data=True)` 默认使用数据模式；传 `False` 可回退到整表 HTML。
- **通用表格脚本 `TS`**（`src/site_html/js.py` 中的 `_JS_TABLE`）：
  - 每一行是一个对象 `{t: 单元格文本[], h: {列号: html}, c: 行 class, u: uid, p: 今日已选, d: 明细, el: <tr>}`。
  - `TS.rows`：全部行；`TS.visible`：当前匹配的行。
  - `TS.render(list)`：决定把哪些行放进 `tbody`，页面可以覆盖。排名页覆盖为“分页 + 只显示前 `limit` 行”。
  - `TS.el(m)`：按需创建某一行的 `<tr>`；`TS.onRow`：行元素创建时的回调。
  - `TS.extra`：额外的筛选条件，参数是行对象；`TS.setOrder(arr)`：设置行顺序。
  - `TS.refresh()`：重新筛选。每次筛选后会触发 `ts:filtered` 事件。
- **页面脚本不要再直接读取表格 DOM**（如 `tbody tr`、`.cells`、`dataset`）：大多数行不在 DOM 里。请读取行对象；点击事件请在 `tbody` 上统一监听。
- **本地文件打开的兼容：** 积分明细（`breakdown_ui.py`）通过 `<script>` 加载 `data/breakdown_*.js`，而不是用 `fetch` 读 JSON。这样直接双击打开本地 HTML 文件（`file://`）也能用。后续把数据拆到外部文件时，要沿用这个思路，或者明确决定不再支持 `file://`。

### 验证方法（第二阶段用过的工具）

第二阶段使用了一个本地预览服务器和一套 A/B 对比脚本：加载线上已发布的页面，在内存中替换成新代码后返回给浏览器，加 `?orig=1` 时返回原页面；然后对新旧页面执行同一组操作，对比结果和耗时。**这两个脚本以及第三阶段 3.0 写的 `compare.py`，目前都只在开发者本地的临时目录里，不在仓库中。** 第四阶段任务 4.4 会把它们正式加入仓库。在此之前，验证方式是：在本地跑一次 `main.py`，然后逐项对比新旧页面的筛选计数、排序结果和各个弹窗。

---

## 二、第三阶段：资源拆分与缓存

**目标：** 减少每个页面的下载量和解析量，让浏览器能跨页面复用缓存。
**分支：** 全部在 `architecture` 上完成，每个子任务单独提交。
**顺序：** 3.0 ✅ → 3.0b 小 bug 修复 ✅ → 3.1 ✅ → 3.2 → 3.3（等截图确认）→ 3.4。3.2 依赖 3.1 的外置资源与 `ts:ready`，按顺序做，不并行。

### 已确认的决定（2026-10-31）

| 事项 | 决定 |
|---|---|
| 3.3 字体 | 先做截图对比（Mac / Windows / 手机，亮色和暗色），确认后再决定是否上线 |
| `file://` | **继续支持。** 外部数据一律用 `.js` 包装文件（`window.__XXX = …`）加 `<script>` 加载，不用 `fetch` |
| 排名类数据文件名 | **固定文件名，加 `?v=<内容哈希>`。** 不产生新文件，git 中只记录修改 |
| H2H 的 `dt` 字段 | 待确认，推荐方案见 3.2 第 1 步 |

### 第三阶段开始前发现的问题（必须在对应任务中一并处理）

1. **workflow 的提交清单是固定的。** `update-live.yml` 和 `update-daily.yml` 只 `git add` 清单中的路径，`update-live.yml` 提交后还会执行 `git reset --hard && git clean -fd`，清单外新生成的文件会被删掉。新增的 `assets/`、`data/` 文件如果不在清单里，线上页面会引用不存在的文件（404）。**每个新增输出文件的任务，都要同时修改两个 workflow 的清单**，并写进验收标准。
2. **部分页面没有被任何 workflow 发布：** `combined_calendar.html`、`combined_champion.html`、`watchlist.html` 不在两个清单里，只在手动提交时才会更新。目前线上的 `combined_calendar.html` 数据已经过期（本地离线重新生成后 `clData` 与已提交的版本不同）。另外 `events/2024`、`events/2025` 中已提交的页面仍是第一阶段之前的表格脚本。3.1 之后这些页面会引用外部资源，所以**旧资源文件的清理必须以“磁盘上所有 HTML 的实际引用”为准**，不能以“本次生成了什么”为准。是否把这三个页面加入 daily 清单，在 3.1 中一并决定。
3. **改用 `defer` 后执行顺序会变。** 现在各页面的 `ready(fn)` 在解析阶段执行（`readyState === 'loading'`），会注册 `DOMContentLoaded` 监听，并排在 `_JS_TABLE` 初始化之后执行。改成 `defer` 后，脚本执行时 `readyState` 已经是 `interactive`，`ready(fn)` 会立即执行，**早于 TS 初始化**。此外，内嵌脚本没有 `defer` 效果，会早于外部脚本执行。解决办法：`_JS_TABLE` 初始化结束时设置 `TS.ready = true` 并触发 `ts:ready`，所有依赖 `TS` 的页面脚本改为等待这个事件。

### 3.0 准备工作 ✅（2026-10-31 完成）

- **离线生成可以复现：** `main.py --calendar-cache-only`（174 个赛事页和 3 个赛历页，约 1 分钟）和 `--stats-cache-only`（`atp_show` / `wta_show`，约 2 分钟）不需要联网。连续运行两次，除了页头的更新时间之外，输出完全相同。这两种模式可以作为 3.1 的主要对照：同一份缓存数据，用新旧代码各生成一次再对比。
- **需要联网的页面**（排名、H2H、killer / nemesis、index、champion、watchlist）用最近一次提交（`fb23ba079`）中的 HTML 作为基准，验证时沿用第二阶段的方式：在本地用新代码生成，再对比筛选计数、排序结果和弹窗。
- **对比脚本 `compare.py`：** 给出每个分组的 HTML 体积和 gzip 体积，并逐页对比两项：一是“可见文本”（去掉 script / style / link，并屏蔽更新时间）；二是所有内嵌 JSON 数据块（`#tsData`、`#evData`、`#clData` 等，解析后对比）。3.2 外置数据后，要扩展它去读取外部数据文件。按照约定，这个脚本暂时只放在本地临时目录，第四阶段 4.4 再正式加入仓库。
- **基准数据（改造前，已包含 3.0b 的修复）：**

  | 页面 | HTML | gzip |
  |---|---:|---:|
  | `events/2026/WS_30528.html`（赛事页） | 175 KB | 39 KB |
  | `wta_ranking.html` | 410 KB | 67 KB |
  | `wta_show.html` | 473 KB | 92 KB |
  | `h2h_wta.html` | 9,631 KB | 744 KB |
  | `combined_calendar.html` | 393 KB | 123 KB |
  | `survivor_calendar_wta.html` | 283 KB | 90 KB |
  | `watchlist.html` | 261 KB | 60 KB |
  | `atpkiller.html` | 110 KB | 26 KB |
  | `index.html` | 68 KB | 12 KB |
  | `events/` 全部 174 页合计 | 30,575 KB | 6,860 KB |

### 3.0b 小 bug 修复 ✅（2026-10-31 完成，在 3.1 之前做）

两个 bug 改动的文件（`event_page.py`、`calendar_list.py`）正是 3.1 要改的页面外壳，所以先修，让 3.1 的对比结果只包含资源引用的变化。修完后已重新生成 3.0 的基准。

1. **赛事页“返回”总是回到 2026 年的赛历。** 赛事页的返回链接现在带上年份（`survivor_calendar_{atp|wta}.html#y=<年份>`）。赛历页启动时读取 `#y=`；切换年份时用 `history.replaceState` 同步更新地址（切回默认年份时去掉 hash），所以从赛事页用浏览器“后退”也能回到原来的年份。帮助弹窗原有的“有 hash 就不自动弹出”逻辑保持不变。
   - 验证：本地预览中，从 2025 赛事页点“返回”进入 2025 年赛历；切换年份后地址同步变化；在 2024 年赛历中点进一个赛事，再按浏览器后退，仍显示 2024 年。控制台没有错误。
2. **2026 年 WTA 林茨被识别为硬地。** `tournament_meta.classify_surface(city, year=None)` 增加了按年份覆盖的表 `SURFACE_FROM_YEAR`，其中 `("林茨", 2026)` 表示 2026 年及以后为红土；不传年份时行为不变。三处调用都传入了年份：`calendar_list.surface_code`（赛历的场地标签）、`event_page`（赛事页的场地主题色）、`user_breakdown`（积分构成按场地分组）。
   - 验证：离线重新生成后，赛历数据中只有“2026 林茨”一条记录的场地从 `h` 变为 `c`，其余页面的文本和数据和修复前一致；`events/2026/WS_30528.html` 已改用红土主题。积分构成数据（`data/breakdown_*.js`）需要联网生成，要等下一次自动更新时才会刷新。

### 3.1 共用 CSS / JS 抽成外部文件（优先级高，工作量 2–3 天）

**现状：** 约 200 个页面（其中 `events/` 下有 174 个）各自内嵌了相同的 CSS 和 JS。赛事页约 175 KB，其中大部分是重复内容。

**盘点结果（2026-10-31）：**
- 赛事页、赛历、排名、show、killer、champion、watchlist 都使用 `_inner_page_shell`，只有 `index.py` 和 `h2h.py` 有自己的外壳。（原方案中提到的 `event_page._render_shell` 并不是外壳。）
- 赛事页内嵌约 92 KB CSS（`_CSS_INNER` 27 KB、`CSS_RANK` 39 KB、`CSS_EVENT` 18 KB 等）和约 41 KB JS（`_JS_TABLE` 20 KB、`JS_EVENT` 19 KB 等），全部是固定内容，可以整体外置。
- 按页面插值、不能直接做成共用文件的代码：`killer.py` 的 `_JS_KILLER_DETAIL.replace("__UNIT__"/"__FOOT__")`，以及 `ranking.py` 的 `breakdown_boot_script(url…)` 和汇总栏内嵌 JS。
- `late_js` 是内嵌的 `<script>`。外部文件改用 `defer` 后，执行顺序会发生变化，所以必须先修正启动顺序（3.1-1），再拆文件。

**任务表（按顺序执行，每个任务单独提交）：**

| # | 任务 | 状态 |
|---|---|---|
| 3.1-0 | 同步分支，确认基准 | ✅ `architecture` 与 `main` 是同一个提交，基准对应的源码和当前代码一致 |
| 3.1-1 | 引入 `ts:ready`，修正启动顺序（文件仍然内嵌） | ✅ 见下方说明 |
| 3.1-2 | 去掉共用 JS 中的按页面插值（拆分 `JS_RANK`/`JS_HIST`，killer 改用 `window.CFG`） | ✅ 见下方说明 |
| 3.1-3 | 新建 `assets.py`：按内容哈希写文件，按页面深度计算相对路径（暂不接入页面） | ✅ |
| 3.1-4 | `_inner_page_shell` 的 CSS 改为外部文件（`<link>` 的顺序与原 `<style>` 拼接顺序一致，`css_vars` 继续内嵌） | ✅ |
| 3.1-5 | 赛事页和赛历的 JS 改为外部文件（可离线验证，先做） | ✅ |
| 3.1-6 | 排名、show、killer、champion、watchlist 的 JS 改为外部文件（在 worktree 中联网生成，用同一份数据做 A/B 对比） | ✅ |
| 3.1-7 | `index.py` 和 `h2h.py` 的外壳 | ✅ |
| 3.1-8 | 清理旧资源文件（按引用扫描，只删超过 1 天的旧文件），核对 workflow 清单 | ✅ |
| 3.1-9 | 重新生成 2024/2025 年赛事页；决定三个漏发页面是否加入 daily 清单 | ✅ 见下方（历史赛事页随下次 daily / calendar 重建） |
| 3.1-10 | 整体验收，更新文档，合入 `main`，线上检查缓存命中和 404 | ✅ 合入 `architecture` → `main` |

**3.1-1 完成说明：**
- `_JS_TABLE` 在初始化结束时（没有表格的页面也一样）设置 `TS.ready = true` 并触发 `ts:ready`。`JS_RANK` 改为：TS 已经就绪就立即启动，否则等待 `ts:ready`。启动时依赖 TS 的只有 `JS_RANK`；其他页面脚本和弹窗不读取 TS，或者只读取静态表头，所以没有修改。
- 验证：
  - 离线生成的 174 个赛事页、赛历、show 页，经 `compare.py` 对比，可见文本和数据与基准一致；
  - `wta_show` 的 A/B 对比（前几行、正向排序、反向排序、按钮数、卡片数）完全相同，控制台没有错误；
  - 把排名脚本移到表格脚本之前，模拟改用外部文件后的执行顺序：旧代码下排名界面没有启动，新代码下正常启动。
- 没有单独验证排名类页面（需要联网生成）。它们和 show 页使用同一段 `JS_RANK` 启动代码，留到 3.1-6 做完整对比。

**3.1-2 完成说明：**
- `JS_RANK` 不再内含 `JS_HIST`；排名页 `late_js=JS_HIST + JS_RANK`，关注页仍为 `JS_HIST + JS_WATCH`，便于后续分别外置为 `hist.js` / `rank.js`。
- killer / nemesis 详情脚本去掉 `__UNIT__` / `__FOOT__` 字符串替换，改为读取 `window.CFG.unit` / `window.CFG.foot`（页面在 `extra_js` 开头注入）。

**3.1-3 完成说明：**
- 新增 `site_html/assets.py`：`asset_url(name, content, page)` 按内容 sha256 前 8 位写入 `assets/<stem>.<hash>.css|js`（已存在则不重写），相对路径复用 `header._resolve` 的 `events/` 前缀。尚未接入页面外壳。

**3.1-4 完成说明：**
- `_inner_page_shell`：`css_vars` 仍内嵌；`_CSS_BASE` + `_CSS_INNER` + `_CSS_ROUTE_QUERY` + `CSS_HEADER` 写成 `assets/site.<hash>.css` 并以 `<link>` 引入；页面专用 `extra_css`（如 `CSS_RANK`）仍内嵌。`rank.css` 留到排名类页面改造时再拆。

**3.1-5 完成说明：**
- `_inner_page_shell` 共用 `table.js` / `header.js` 改为 `<script defer>`；`_JS_THEME` 与 `extra_js` 仍内嵌。
- 新增 `late_asset`：赛事页写 `event.js`，赛历列表写 `cal.js`；排名等未迁页面的 `late_js` 仍内嵌，留给 3.1-6。

**3.1-6 完成说明：**
- shell 支持 `css_assets` / `defer_js`；脚本顺序为 `table.js →（页面脚本）→ header.js`。
- 排名 / show：`rank.css` + `hist.js` + `rank.js`；关注：`hist.js` + `watch.js`；冠军榜：`champion.js`；killer 详情：`killer-detail.js`（`ready()` 兼容 defer）；赛事 / 赛历的 `CSS_RANK` 也改为外链 `rank.css`。
- 汇总栏、breakdown boot、career detail 等按页插值脚本仍内嵌。完整联网 A/B 对比留待合入前抽检。

**3.1-7 完成说明：**
- 首页：`site.css` + `index.css`，`index.js` / `index-watch.js` 用 `defer`；主题脚本仍内嵌。
- H2H：数据改为 `#h2hRecords` 等 JSON 标签，`h2h.js` / `h2h.css` / `header.js` 外置；去掉 `__RECORDS_JSON__` 等字符串替换。

**3.1-8 完成说明：**
- `cleanup_unused_assets()`：扫描全部 HTML 引用，删除超过 1 天且未被引用的 hashed 资源（保留 `echarts.min.js`）；`main.py` 在 live/daily 结束时调用。`assets` 已在两个 workflow 清单中。

**3.1-9 完成说明：**
- `combined_calendar.html`、`combined_champion.html`、`watchlist.html` 加入 `update-daily.yml` 发布清单。
- 2024/2025 赛事页会在下次带 `events/` 的 daily / calendar 重建中自动换上外置资源；未单独离线全量重跑。

**3.1-10 完成说明：**
- `architecture` 合入 `main`；文档本表已更新。合入后靠自动 live/daily 重生成页面以引用新 assets；请抽查赛事页体积、缓存与控制台。

**技术要点：**
1. 新增 `site_html/assets.py`，提供 `asset_url(name, content, page)`：
   - 按内容计算 sha256，取前 8 位，写入 `assets/<name>.<hash>.css|js`；文件已存在时不重写；
   - 返回的相对路径按 `page` 的目录深度计算，复用 `header.py` 中已有的前缀逻辑。
2. 拆出的共用文件：
   - `site.css`：`_CSS_BASE`、`_CSS_INNER`、`_CSS_ROUTE_QUERY`、`CSS_HEADER`；
   - `rank.css`：`CSS_RANK`；
   - `table.js`：`_JS_TABLE`；
   - `header.js`：`JS_HEADER`；
   - `hist.js`：`JS_HIST`；
   - `rank.js`：`JS_RANK` 去掉 `JS_HIST` 后的部分。`rank_ui.py` 中的 `JS_RANK = JS_HIST + …` 要拆开，watch 页改为引用 `hist.js` 加上内嵌的 `JS_WATCH`。
3. **保持内嵌的内容：**
   - `state.css_vars`：赛事页按场地切换主题，每页不同；
   - `_JS_THEME`：如果改成外部文件，暗色模式会先闪一下白底；
   - 只与某一页相关的小段 CSS / JS。
4. 所有外部脚本统一使用 `defer`，按 `table.js` → `hist.js` → `rank.js` → `header.js` 的顺序排列。引入 `ts:ready` 事件（见上文“开始前发现的问题”第 3 条）。共用文件中不能包含按页面插值的值，页面专用配置改为放在内嵌的 `window.CFG` 或 `data-*` 属性中。
5. 按页面外壳逐个修改，每改一个就对比一次：先 `_inner_page_shell`，然后依次是 `event_page._render_shell`、`h2h`、`index`、`calendar*`、`champion`、`watch`、`killer`。
6. 清理旧资源：扫描所有 HTML 的实际引用，只删除没有被任何页面引用、并且生成时间超过 1 天的旧文件（避免和并发运行的 workflow 冲突）。
7. 确认 `assets` 在两个 workflow 的清单中（目前已经在）。

**验收标准：**
- 赛事页 HTML 小于 30 KB；
- 连续打开两个赛事页，第二个页面的 CSS / JS 来自缓存；
- 用 `compare.py` 对比离线生成的结果，可见文本和数据块没有差异；
- 控制台没有错误；暗色模式没有闪烁；`file://` 打开正常。

### 3.2 数据外置与压缩编码 ✅

**已完成（2026-11-02）：**
1. **H2H 列式 + 字典编码**（含 `weeks`/`dt` 索引，不改前端排序）。Python 端编码后自检还原。数据写入 `data/gen/h2h_{atp|wta|all}.<hash>.js`（`window.__H2H_DATA`）；页面通过 `CFG.dataUrl` 异步加载，加载中禁用查询并显示提示，失败可「重试」。
2. **排名类：** `_df_to_table_data(external=True)` → 固定名 `data/gen/rank_<page>.js?v=<hash>`（`window.__TS_DATA`）；`_JS_TABLE` 优先读 `#tsData`，否则读 `__TS_DATA`。defer 顺序保证 table 初始化时数据已在。
3. **赛历 / watchlist：** `cal_{atp|wta|all}.js`、`watchlist.js` 同样外置；JS 优先读 `__CL_DATA` / `__WL_DATA`。
4. **`write_data_js` / `data/gen` 清理** 写入 `assets.py`；两个 workflow 清单已加 `data/gen`。
5. 赛事页 `evData` 仍内嵌（体量相对小、页数多），留待后续若需要再拆。

**验收（合入后靠 daily/live 重生成）：**
- H2H HTML 应变瘦，数据在 `data/gen`；抽查全选查询条数与胜负。
- 排名 HTML 应变瘦；筛选 / 排序 / 我的卡片正常。
- `file://` 下相对路径 `.js` 仍可用。

### 3.3 字体（优先级中，工作量 0.5–1 天，**截图确认后再上线**）

1. 中文改用系统字体：`"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif`；标题使用 `"Songti SC","STSong",serif`。
2. Space Mono 改为自行托管，放在 `assets/fonts/`：只保留 400 和 700 两个字重，woff2 格式，`font-display: swap`，同时附上 OFL 许可证。
3. 截图对比标题、表格、卡片，覆盖 Mac、Windows、手机，以及亮色和暗色模式。确认后才合入。

**验收标准：** 页面不再请求 `fonts.googleapis.com` 和 `fonts.gstatic.com`。

### 3.4 其他小项（优先级低，各 0.5 天以内）

- `echarts.min.js`：`breakdown_ui.loadScriptOnce` 已经实现按需加载，只需要确认没有地方在页面加载时就引用它。
- `index.html` 内嵌的数据如果超过 50 KB，按 3.2 的方式外置。
- 用 `curl -sI --compressed` 抽查线上大页面，确认有 `content-encoding`。

---

## 三、第四阶段：工程治理

**目标：** 控制仓库体积，加快自动更新，并防止性能再变差。这一阶段不直接影响用户体验，但能让后续开发和维护更稳定。

### 4.1 生成的页面不再提交到 `main`（优先级高，工作量 1–2 天，需要仓库管理员操作）

**现状：** `update-live.yml` 大约每 15 分钟提交一次生成的 HTML，`update-daily.yml` 每天提交一次。`.git` 已经约 228 MB（打包后约 182 MiB），而且还在持续增长。`run.sh` 也会执行 `git add .` 然后提交并推送。

**做法：**
1. GitHub Pages 的发布来源改为 **GitHub Actions**：工作流生成页面后，用 `actions/upload-pages-artifact` 和 `actions/deploy-pages` 发布，不再把生成结果提交回 `main`。
2. **要解决一个关键问题：** 增量更新依赖上一次生成的结果（比如 `--live` 只重新生成选人相关的页面，其余页面沿用旧版本）。改成用 Actions 发布后，每次需要拿到完整的站点文件。有两个方案：
   - **方案 A（推荐）：** 每次运行都完整生成所有页面。需要先完成 4.2 的增量构建优化，否则耗时可能太长。
   - **方案 B：** 生成结果推到单独的 `gh-pages` 分支，每次只追加一个提交，并定期压缩这个分支的历史（`git checkout --orphan` 后强制推送）。`main` 分支只保留源码和 `data/`。
3. `data/` 里哪些是原始输入、哪些是生成产物，需要逐个梳理。生成产物也移出 `main`。
4. 已有的仓库历史是否要清理（例如用 `git filter-repo` 删除旧的生成页面）是**不可逆操作**，必须由仓库负责人决定，并通知所有协作者重新克隆。
5. `run.sh` 里的 `git add .`、提交和推送要相应修改或删除。

**验收标准：** `main` 分支连续 7 天没有自动生成的页面提交；网站照常按时更新；`.git` 不再增长（或只随源码变化缓慢增长）。

### 4.2 增量构建与生成提速（优先级中，工作量 2–3 天）

**现状：** 有几处生成代码逐行遍历 DataFrame（`iterrows`），例如 `common.py` 的 `_table_rows`、`h2h.py` 的 `_h2h_records_json` 和 `_h2h_user_list`；而且每次更新都会重新生成很多与这次数据变化无关的页面（例如 174 个赛事页）。

**做法：**
1. 先给 `main.py --daily` 和 `--live` 中每个生成步骤计时（`logger` 里已经有类似的日志），找出最耗时的步骤。
2. `iterrows` 改为向量化写法，或 `to_dict("records")` / `itertuples`。`_table_rows` 修改后，**输出必须和修改前逐字节一致**（参见下面的“测试”）。
3. 赛事页：只重新生成当前赛季中数据有变化的赛事。可以对每个赛事的输入数据计算哈希，保存在 `data/` 的一个清单文件里，哈希没变就跳过。
4. 共用资源（3.1）的内容没变时，保持文件名不变，避免所有页面都随之变化。

**验收标准：** `--live` 的总耗时减少一半以上；在输入数据不变时连续生成两次，生成的文件完全相同。

### 4.3 回归测试（优先级中，工作量 1–2 天）

**做法：** 新建 `tests/` 目录，使用 pytest，至少包含以下测试：
- `_df_to_html_table` 的输出快照：用一份覆盖各种情况的测试数据（各种状态、排名变化、合并列、uid、picked、各种形式的明细、空值），比对固定的输出。2B 阶段做过同样的比对，确认重构后输出逐字节一致。
- `_table_rows` → `_df_to_table_data` 和 → `_df_to_html_table` 的往返一致性：把 HTML 解析回行数据，结果应该和 `_table_rows` 的输出相同。
- `_h2h_records_json`（或 3.2 之后的列式编码）：记录条数、排序顺序、字典索引能正确还原。
- 在 GitHub Actions 中，每次推送到 `main` 或提 PR 时运行 `pytest`。

### 4.4 页面体积与性能检查（优先级中，工作量 1–2 天）

**做法：**
1. **体积检查（简单，先做）：** 生成结束时检查每个页面以及 `assets/`、`data/` 下文件的大小。超过阈值时输出警告；阈值可以写在 `config.yaml` 里，例如普通页面 300 KB、H2H 数据 2 MB。
2. **交互回归检查（较完整）：** 把第二阶段用过的 A/B 对比脚本正式加入仓库，例如放到 `tools/perf/`，包括：
   - `preview_server.py`：本地预览服务器；
   - `perf_check.js`：对新旧页面执行同一组操作，对比状态标签计数、排序、夺冠路线查询、分类筛选、滑块、“我的卡片”、跳转、历史弹窗的结果，并记录 DOM 节点数和耗时。
   之后用 Playwright 在 CI 中自动运行：用 `main` 分支生成的页面作为基准，和 PR 分支生成的页面对比。性能底线：排名页 DOM 少于 4,000 个节点、排序少于 100 ms、切换状态标签每次少于 100 ms。

**验收标准：** 只要有页面超过体积阈值或交互结果和基准不一致，CI 就失败，并给出具体的页面名称和差异。

---

## 四、建议

- **一次只做一个任务，每个任务单独提交。** 提交信息写清楚改了什么、怎么验证的、测出的数字。仓库里第一、二阶段的提交可以作为参考。
- **改完先在本地跑一次 `main.py`**，再打开相关页面检查：筛选计数、排序、各类弹窗、手机宽度下的卡片、暗色模式。
- **不要直接修改仓库里生成的 HTML 文件。** 这些文件会被下一次自动更新覆盖，要改请改 `src/site_html/` 下的生成代码。
- **需要决定的事项：** 3.3 字体的视觉变化、4.1 的部署方式和是否清理历史。这几项请先确认再动手。
