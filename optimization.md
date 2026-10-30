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

第二阶段使用了一个本地预览服务器和一套 A/B 对比脚本：加载线上已发布的页面，在内存中替换成新代码后返回给浏览器，加 `?orig=1` 时返回原页面；然后对新旧页面执行同一组操作，对比结果和耗时。**这两个脚本目前只在开发者本地的临时目录里，不在仓库中。** 第四阶段任务 4.4 会把它们正式加入仓库。在此之前，验证方式是：在本地跑一次 `main.py`，然后逐项对比新旧页面的筛选计数、排序结果和各个弹窗。

---

## 二、第三阶段：资源拆分与缓存

**目标：** 减少每个页面的下载量和解析量，让浏览器能跨页面复用缓存。
**建议顺序：** 3.1 → 3.2 → 3.3 → 3.4。各任务之间基本互不依赖，可以并行，但 3.1 和 3.2 都会改 `_inner_page_shell`，同时进行时要注意代码冲突。

### 3.1 共用 CSS / JS 抽成外部文件（优先级高，工作量 2–3 天）

**现状：** 约 200 个页面（其中 `events/` 下有 174 个）各自内嵌了相同的 CSS（40–100 KB）和 JS（20–80 KB），浏览器无法跨页缓存。每个赛事页约 155 KB，其中绝大部分是重复内容。

**涉及文件：**
- 页面外壳：`common.py` 的 `_inner_page_shell`、`event_page.py` 的 `_render_shell`、`h2h.py`、`index.py`、`calendar*.py`、`champion.py`、`watch.py`、`killer.py`
- 共用内容：`css.py`（`_CSS_BASE`、`_CSS_INNER` 等）、`header.py`（`CSS_HEADER`、`JS_HEADER`）、`js.py`（`_JS_THEME`、`_JS_TABLE`）、`rank_ui.py`（`CSS_RANK`、`JS_RANK`）、`breakdown_ui.py`

**做法：**
1. 新增一个生成步骤（例如 `site_html/assets.py`），把共用的 CSS / JS 写到 `assets/site.<hash>.css`、`assets/table.<hash>.js`、`assets/rank.<hash>.js` 等文件。`<hash>` 取内容哈希的前 8 位，内容变了文件名就会变。
2. 各页面外壳改为通过 `<link rel="stylesheet">` 和 `<script src defer>` 引用这些文件。**只与某一页相关**的小段 CSS / JS（例如 killer 弹窗）仍然内嵌。
3. 注意脚本执行顺序：目前 `_JS_TABLE` 在 `DOMContentLoaded` 时初始化，`JS_RANK` 作为最后一个 `<script>` 执行。改成外部文件后，`table.js` 必须排在 `rank.js` 之前，统一用 `defer` 可以保证顺序。
4. 旧的哈希文件需要清理：生成时删除 `assets/` 下没有被任何页面引用的旧文件，或者只保留最近 N 个版本。

**注意事项：**
- 页面的相对路径深度不同（`events/2026/*.html` 比根目录的页面深两级），引用路径要按页面位置计算。可以参考 `_inner_page_shell` 里的 `page=` 参数现在是怎么处理返回链接的。
- GitHub Pages 的 `Cache-Control` 固定为 `max-age=600`，**不能自定义**。所以带哈希的文件名主要带来两个好处：同一会话内切换页面时直接复用缓存；10 分钟后再访问时，浏览器发条件请求，服务器返回 304，不必重新下载。长期强缓存要等第四阶段换部署方式之后才能实现。
- `JS_RANK` 中的 `JS_HIST` 也被 `watch.py` 使用，拆分时注意两边的依赖。

**验收标准：**
- 赛事页 HTML 从约 155 KB 降到 30 KB 以下；
- 连续打开两个不同的赛事页，第二个页面的 CSS / JS 来自缓存（在开发者工具 Network 面板查看）；
- 所有页面的功能和改之前一致，控制台没有报错。

### 3.2 数据外置与压缩编码（优先级高，工作量 3–4 天）

**现状：**
- H2H：约 9 万条记录以 JSON 对象数组的形式内嵌在页面里（6.7–8.2 MB），每条都重复完整的中文用户名、球员名、赛事名。
- 排名类页面：`#tsData` 内嵌，每页 300–450 KB。
- 日历页、watchlist：分别内嵌 140–285 KB 的数据。

**涉及文件：** `h2h.py`（`_h2h_records_json` 和页面 JS）、`common.py`（`_table_data_markup`）、`ranking.py`、`killer.py`、`calendar.py`、`calendar_list.py`、`watch.py`

**做法：**
1. **H2H 改为按列存储 + 字典编码（收益最大）：**
   ```json
   {"users":["…"],"players":["…"],"tours":["…"],
    "u":[0,0,1,…],"p":[…],"t":[…],"d":[…],"s":[…],"r":[…]}
   ```
   每条记录只保存整数索引，并去掉前端没有用到的 `dt` 字段。注意：`sortRecords()` 目前按 `dt` 排序，去掉 `dt` 之前，要在 Python 端先按“周倒序、Day 倒序、赛事、胜在前、球员拼音”排好顺序。拼音排序可以用 `pypinyin` 生成排序键；如果不想新增依赖，可以保留一个整数类型的周序号字段代替 `dt`。前端加载后，用这些数组构造与现在相同的行对象，`runQuery` 等函数基本不用改。预计数据从 8 MB 降到约 1–1.5 MB，gzip 后约 300 KB。
2. **数据文件独立：** 生成 `data/h2h_wta.<hash>.json` 等文件，页面先显示筛选界面，再加载数据（显示“加载中”）。为了兼容 `file://`，可以像 `breakdown_ui.py` 一样同时生成 `.js` 包装文件（`window.__H2H_WTA = …`），通过 `<script>` 加载。
3. **排名类页面：** `_table_data_markup` 增加一个可选参数，把 `#tsData` 改为外部文件。`_JS_TABLE` 读取数据的方式改成异步：数据就绪后再执行原来的初始化。因为排名页的脚本（`JS_RANK`）依赖 `TS.rows`，**必须等表格初始化完成后再启动**。建议在 `_JS_TABLE` 初始化完成后触发 `ts:ready` 事件，`JS_RANK` 监听这个事件再启动。
4. **日历页和 watchlist：** 用同样的方式外置数据，优先处理 `combined_calendar.html`（约 285 KB 脚本）。

**注意事项：**
- 排名页每 15 分钟更新一次。数据文件名带哈希，可以避免浏览器缓存了旧数据；HTML 本身没有哈希，GitHub Pages 最多缓存 10 分钟，可以接受。
- 首屏会多一次网络请求。对排名页来说，“我的卡片”和“汇总”在数据加载完成前要显示占位内容，不能出现空白或报错。

**验收标准：**
- H2H 页面传输体积（gzip 后）降到 500 KB 以下；全选查询结果与现在完全一致（记录条数、胜负数、前 50 行顺序）；
- 排名页 HTML 降到 100 KB 以下，A/B 对比结果和现在一致；
- 直接双击打开本地 HTML 文件（`file://`）时，页面仍然可用；如果决定不再支持，需要在 README 中写明。

### 3.3 字体（优先级中，工作量 0.5–1 天）

**现状：** 每个页面都从 `fonts.googleapis.com` 加载 Noto Serif SC、Noto Sans SC（多个字重）和 Space Mono（见 `css.py` 的 `_FONTS`）。中文字体文件很大；在国内访问 Google Fonts 可能很慢甚至失败，导致文字迟迟不显示或页面跳动。

**做法（按推荐顺序）：**
1. 中文改用系统字体：`font-family: "PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif`，不再加载 Noto Sans SC 和 Noto Serif SC。标题如果需要衬线效果，可以用 `"Songti SC","STSong",serif`。
2. Space Mono（主要用于数字和英文）改为放在 `assets/fonts/` 下自行托管，只保留 400 和 700 两个字重，使用 `font-display: swap`。
3. 先截图对比改前改后的标题、表格和卡片，**确认视觉效果可以接受**后再上线。

**验收标准：** 页面不再请求 `fonts.googleapis.com` 和 `fonts.gstatic.com`；在国内网络下，首屏文字立即显示。

### 3.4 其他小项（优先级低，各 0.5 天以内）

- `assets/echarts.min.js` 已经是外部文件。确认它只在打开积分构成弹窗时才加载（看 `breakdown_ui.py` 里的 `loadScriptOnce`）；如果是页面加载时就加载，改成按需加载。
- `index.html` 内嵌的天气、日历数据如果超过 50 KB，按 3.2 的方式外置。
- 抽查 `wta_show.html`、`h2h_wta.html` 等大页面在 GitHub Pages 上的响应头，确认有 `content-encoding: gzip`（GitHub Pages 默认会压缩）。

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
