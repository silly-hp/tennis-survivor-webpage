# 签表幸存者数据中心

一个专为网球签表幸存者游戏玩家设计的数据查询平台，整合了 ATP 与 WTA 赛事的积分、排名、战绩等核心统计数据。

## 功能模块

| 页面 | 功能说明 |
|------|----------|
| [首页](index.html) | 导航总览，快速跳转各功能模块 |
| [ATP 幸存者积分](atp_ranking.html) | ATP 球员实时幸存者积分排名 |
| [WTA 幸存者积分](wta_ranking.html) | WTA 球员实时幸存者积分排名 |
| [ATP Race 排名](atp_race_ranking.html) | ATP 年终总决赛 Race to Turin 积分 |
| [WTA Race 排名](wta_race_ranking.html) | WTA 年终总决赛 Race to Riyadh 积分 |
| [ATP 冠军榜](atp_champion.html) | ATP 幸存者游戏历届赛事冠军记录 |
| [WTA 冠军榜](wta_champion.html) | WTA 幸存者游戏历届赛事冠军记录 |
| [2026 ATP 终结者](2026atpkiller.html) | 2026 赛季 ATP 淘汰数排行榜 |
| [2026 WTA 终结者](2026wtakiller.html) | 2026 赛季 WTA 淘汰数排行榜 |
| [ATP 历史终结者](atpkiller.html) | ATP 全历史终结者总榜 |
| [WTA 历史终结者](wtakiller.html) | WTA 全历史终结者总榜 |
| [ATP 交手记录](h2h_atp.html) | ATP 任意两名球员历史对阵查询 |
| [WTA 交手记录](h2h_wta.html) | WTA 任意两名球员历史对阵查询 |

## 技术栈

- **前端**：纯 HTML + CSS + 原生 JavaScript，无任何外部框架依赖
- **样式**：CSS 变量实现明暗双主题，配色灵感来自温布尔登（森林绿 `#1b5e37` + 紫色 `#7b3f9e`）
- **字体**：Noto Serif SC（标题）/ Space Mono（数据标签）/ Noto Sans SC（正文）
- **部署**：静态文件直接托管于 GitHub Pages

## 数据来源与更新

页面数据由配套的 Python 数据生成器（`../tennis-draw_survivor/main.py`）自动抓取并渲染为静态 HTML，通过 `run.sh` 脚本完成「拉取 → 生成 → 提交 → 推送」的全流程更新。

原始数据来源：[丘的网球 · 幸存者日历](https://www.live-tennis.cn/zh/survivor/calendar/2026)

## 相关链接

- [旧纳的幸存者冠军榜](https://zechen-3is.github.io/tennis_survivor/)
- [炉网幸存者详细统计](https://xiaokang1217.github.io/tennis_survivor/)
