# 同类项目调研（2026-11-18）

结论：**没有找到与“GitHub 最新 Agent 插件 + B 站最新 DSH 插件 → 核验链接 → Word 清单”完全等价的项目**。
以下是检索到的相近项目，可作为实现参考。

## 直接相关

| 项目 | 星标 | 与本次 Skill 的关系 |
| --- | --- | --- |
| [firecrawl/last30flames](https://github.com/firecrawl/last30flames) | 43 | **最接近的同类**：在时间窗内研究“某个话题真正的新东西”，聚合 Firecrawl Search、Hacker News、Lobste.rs、Bluesky、GitHub 五路信号，由 Agent 写简短简报。差异：通用话题研究，不针对插件，不产出 Word。 |
| [firecrawl/skills](https://github.com/firecrawl/skills) | 159 | Firecrawl 官方 Agent Skills 目录（Claude Code / Cursor / Codex 插件形式），提供通用 search/scrape/crawl 能力，不含插件清单工作流。 |
| [firecrawl/cli](https://github.com/firecrawl/cli) | 689 | Firecrawl CLI 与配套 agent skills，可替代 MCP 作为抓取入口。 |
| [zircote-plugins/sigint](https://github.com/zircote-plugins/sigint) | 24 | Claude Code 的市场情报工具箱，做迭代式研究与趋势建模；偏分析，不做 B 站数据源与文档输出。 |
| [ckckck/UltimateSearchSkill](https://github.com/ckckck/UltimateSearchSkill) | 290 | 双引擎搜索 Skill（Grok + Tavily + FireCrawl），是抓取层组件。 |
| [alex-on-ai/WebReaper](https://github.com/alex-on-ai/WebReaper) | 153 | 自带 Claude Code Skill 的抓取器，是抓取层组件。 |

## DSH 插件发现类

| 项目 | 星标 | 说明 |
| --- | --- | --- |
| [awesome-dsh-plugin/awesome-dsh-plugin](https://github.com/awesome-dsh-plugin/awesome-dsh-plugin) | 25k | 人工维护的 DSH 插件精选列表，非自动采集，也不覆盖 B 站。 |
| [dsh-market/dsh-market](https://github.com/dsh-market/dsh-market) | 12.8k | DSH 内置可视化插件市场（浏览/搜索/一键安装），是分发端而非采集端。 |
| [zhu1090093659/dsh-web](https://github.com/zhu1090093659/dsh-web) | 10.5k | DSH Web 插件聚合生态，同样偏分发。 |
| [lucky8197/dsh-weekly-digest](https://github.com/lucky8197/dsh-weekly-digest) | 2 | DSH 周报插件，但聚合的是 git 提交、会话活动与每日记忆，不采集外部插件。 |
| [hyzyn/dsh-plugin-kit](https://github.com/hyzyn/dsh-plugin-kit) | 68 | DSH 插件开发套件（模板 / monorepo），与采集无关。 |

## 本 Skill 的差异点

1. 双数据源：GitHub（结构化 API）+ B 站（多关键词、需要浏览器渲染，使用 Firecrawl）。
2. 范围是通用的 Agent 插件 / Skill，不限定 DSH；DSH 只是 B 站默认关键词之一。
3. 链接核验：B 站视频简介里的 GitHub 链接会逐条回查仓库，避免只给视频链接。
4. 产物固定：统一的“项目名 + 项目介绍 + 项目链接”Word 文档，可点击超链接。
5. 选取条件可配置，失败路径有降级方案。
6. 批次延续：同一用户再次生成时跳到排名下一段，不重复已交付项目。
