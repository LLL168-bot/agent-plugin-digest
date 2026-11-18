# 选取条件与批次延续说明

报告范围：**GitHub 与 B 站上的 Agent 插件 / Skill**。
所有条件都可在 `config/default.json` 中修改，或用 `--config` 传入局部覆盖文件。

## 一、GitHub

| 条件 | 默认 | 依据 | 调整后的影响 |
| --- | --- | --- | --- |
| Topic | `agent-plugin`、`claude-code-plugin`、`agent-skills`、`claude-skills` | 让仓库自行声明“插件 / Skill”，比全站搜关键词更准 | 增加 `mcp-server` 可扩大工具类范围，噪声也更大 |
| 排序 | 星标降序（`sort=stars`） | 星标是采用广度的粗代理；也是批次延续的排名依据 | 改为 `updated` 更偏“最新”，但会混入低质量新仓库 |
| 最低星标 | 50 | 低星项目通常缺少文档与可安装形态 | 调到 200 更保守；调到 10 更全面 |
| 最近更新 | 365 天 | 一年未更新的插件大概率不适配新版运行时 | 调到 90 天可得到真正活跃的项目，候选会变少 |
| 排除 fork / archived | 是 | 避免镜像与停更仓库 | 关闭后可能重复计数 |
| 必须有描述 | 是 | 无描述无法写出可靠介绍 | 关闭后需人工读 README |
| 关键词白/黑名单 | 空 | 默认不做语义过滤 | 例如 `exclude_keywords: ["tutorial"]` |
| 候选池 / 每批条数 | 60 / 10 | 候选池需足够大，才能支持多批次延续 | 候选池至少应为每批条数的 2–3 倍 |

**排名（固定）**：`sort=stars` → 星标降序，并列按 `full_name` 升序；
`sort=updated` → `pushed_at` 降序，并列按 `full_name` 升序。

## 二、B 站

| 条件 | 默认 | 依据 | 调整后的影响 |
| --- | --- | --- | --- |
| 搜索词 | `agent 插件`、`agent skill`、`Claude Code 插件`、`dsh 插件` | 覆盖通用 Agent 插件 / Skill，同时保留 DSH 入口 | 可加入 `MCP 插件`、`AI 编程插件` 等 |
| 排序 | `pubdate` | “最新”直接对应发布时间 | 改为 `click` 更偏热门而非最新 |
| 合并方式 | 多关键词结果按轮询合并、按 BVID 去重 | 避免同一视频重复，也避免前几个关键词占满候选池 | — |
| 标题排除词 | 个必装 / 推荐3款 / 榜单 / 排行榜 / 合集 / 个插件 | 这些是合集或盘点视频，不对应单一项目 | 用户想看合集时可关闭 `single_plugin_only` |
| 标题必含词 | 空 | 默认不额外限制 | 如设为 `["插件","skill"]` 可进一步收敛 |
| 必须有 GitHub 仓库 | 否 | 部分主题/桌宠类插件只在插件市场分发 | 改为 `true` 可保证可安装链接，但会漏掉部分项目 |
| 优先有仓库 | 是 | “项目链接”优先给仓库，更稳定 | 关闭后严格按发布时间排序 |
| 简介读取上限 | 40 | 控制请求量，降低触发风控的概率 | 提高可覆盖更多候选，但更易 412 |
| 候选池 / 每批条数 | 60 / 10 | 支持多批次延续 | 候选池不足时 `exhausted=true` |
| 请求间隔 / 重试 | 2.5s / 3 次 | B 站对高频匿名请求返回 412 | 网络环境差时可加大间隔 |
| 错误率阈值 | 0.3 | 超过三成失败说明风控已生效 | 达到阈值后改用 Firecrawl 逐页抓取 |

**排名（固定）**：`prefer_github_repo=true` 时先按“有仓库”分组；组内按 `pubdate`
降序；并列按 `bvid` 升序。

## 三、批次延续（不重复输出）

历史文件默认：`~/.agent-plugin-digest/history.json`（可用 `history.state_file` 或
`--state` 覆盖）。同一用户在不同项目中使用时共享同一份历史。

- **稳定 key**：优先 GitHub 仓库 `owner/repo`；没有仓库时用 B 站 `BVID`。
- **跨来源去重**：同一仓库如果在 GitHub 部分已选，B 站部分会跳过并顺延。
- **批次选择**：`history.py select` 读取历史，按固定排名跳过已交付项目，取下一批
  `final_count` 条；输出 `batch`、`remaining`、`exhausted`。
- **记录时机**：只有 Word 成功生成后才执行 `history.py record`。失败、取消、重试
  都不写入历史。
- **批次号**：`batch_count` 每次成功记录加 1；文档副标题和文件名都包含批次号。
- **耗尽**：候选不足时输出剩余条目并提示；不会自动重置历史。
- **重置**：仅在用户明确要求时执行 `history.py reset --yes`。
- **重新生成同一批**：仅用于调试，`history.py select --no-history`；不要重复 record。

## 四、输出

| 条件 | 默认 | 说明 |
| --- | --- | --- |
| 每批条数 | GitHub 10 + B 站 10 | 两节各自按排名取前 N 条 |
| 介绍长度 | 40–120 字 | 超出只告警不失败 |
| 三条字段 | 项目名 / 项目介绍 / 项目链接 | 固定格式，链接渲染为可点击超链接 |
| 文件名 | `{date}_Agent插件Skill清单_第{batch}批_共{total}条.docx` | 可用 `filename_pattern` 修改 |
| 副标题 | `第 {batch} 批 ｜ 共 {total} 条 ｜ 采集日期：{date}` | 可用 `subtitle_pattern` 修改 |
| 输出目录 | `output/`（相对当前目录） | 自动创建；不写死绝对路径 |
| 字体 | 按平台自动 | Windows 微软雅黑、macOS PingFang SC、Linux Noto Sans CJK SC |
| 标签 | 中文 | `output.labels` 可替换为任意语言 |

## 五、覆盖示例

只看最近 90 天、星标 200 以上，B 站搜索通用 Agent 关键词，每批 8 条：

```json
{
  "github": {"min_stars": 200, "updated_within_days": 90, "candidate_limit": 80},
  "bilibili": {
    "keywords": ["agent 插件", "agent skill", "MCP 插件"],
    "final_count": 8,
    "video_info_limit": 60
  },
  "history": {"state_file": "~/.agent-plugin-digest/history.json"},
  "output": {"dir": "reports", "filename_pattern": "{date}_Agent插件_第{batch}批_{total}条.docx"}
}
```

```bash
python "<skill-dir>/scripts/github_plugins.py" --config my-config.json --out .tmp/github.json
python "<skill-dir>/scripts/history.py" select \
  --github .tmp/github.json --bilibili .tmp/bili_ranked.json \
  --config my-config.json --out .tmp/next.json
```

## 六、不可自动化的部分

- 介绍文案必须基于仓库描述、README 或视频简介，不能编造功能。
- “是否真的算 Agent 插件 / Skill”仍需 Agent 判断；脚本只做机械过滤。
- 但**顺序不由 Agent 调整**：批次延续依赖脚本输出的固定排名。
