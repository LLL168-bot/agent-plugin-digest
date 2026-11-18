---
name: agent-plugin-digest
description: 采集 GitHub 与 B 站上最新的 Agent 插件 / Skill，按可配置条件排序并核验项目链接，生成“项目名+项目介绍+项目链接”的 Word 清单；内置批次延续，同一用户再次生成时自动跳过已交付项目，按同一排名继续输出下一批。用户提到“爬取/整理最新 agent 插件、agent skill、插件榜单/周报/清单、生成 Word 报告”时使用。
---

# Agent 插件 / Skill 搜索报告

在 **GitHub** 与 **B 站** 上采集 Agent 插件 / Skill，按可配置条件排序、核验链接，生成
Word 清单。默认 **20 条**（GitHub 10 + B 站 10），并且支持**批次延续**：

- 第 1 次运行输出排名第 1–10 的内容；
- 同一用户第 2 次运行自动跳过已交付项目，输出排名第 11–20 的内容；
- 以此类推，直到候选池耗尽。

## 环境要求

- Firecrawl MCP：`firecrawl_search`、`firecrawl_scrape`（B 站搜索页需要浏览器渲染）。
- Python 3.10+ 与 `python-docx`。
- 可选 `GITHUB_TOKEN`（提高 GitHub 搜索限额）。
- 命令中的 Python：Windows 用 `python`，macOS/Linux 用 `python3`；`<skill-dir>` 指本
  SKILL.md 所在目录。所有路径加引号，脚本内部使用 `pathlib`，Windows/macOS 通用。

```bash
python -c "import docx" || pip install python-docx
```

## 可配置的选取条件

配置文件为深合并：只需写要覆盖的字段。

```json
{
  "github": {"topics": ["agent-plugin", "agent-skills"], "min_stars": 200, "candidate_limit": 80},
  "bilibili": {"keywords": ["agent 插件", "agent skill"], "candidate_limit": 80},
  "history": {"enabled": true, "state_file": "~/.agent-plugin-digest/history.json"},
  "output": {"dir": "reports"}
}
```

| 配置项 | 默认 | 作用 |
| --- | --- | --- |
| `github.topics` | `agent-plugin, claude-code-plugin, agent-skills, claude-skills` | 圈定插件 / Skill 范围 |
| `github.sort` | `stars` | `stars` 或 `updated`；决定批次的排名顺序 |
| `github.min_stars` | `50` | 过滤低质量仓库 |
| `github.updated_within_days` | `365` | 只保留近期活跃项目 |
| `github.include_keywords` / `exclude_keywords` | 空 | 按名称/描述做关键词白/黑名单 |
| `github.candidate_limit` / `final_count` | `60` / `10` | 排名候选池 / 每批条数 |
| `bilibili.keywords` | `agent 插件, agent skill, Claude Code 插件, dsh 插件` | 多关键词检索，结果合并去重 |
| `bilibili.order` | `pubdate` | 按发布时间取最新 |
| `bilibili.exclude_title_keywords` | 合集/榜单类词 | 排除“6 个必装”“排行榜”等非单插件视频 |
| `bilibili.title_include_keywords` | 空 | 可选的标题必含词 |
| `bilibili.single_plugin_only` | `true` | 是否应用上述标题过滤 |
| `bilibili.require_github_repo` | `false` | 是否强制要求插件有 GitHub 项目页 |
| `bilibili.prefer_github_repo` | `true` | 有仓库的候选排名更靠前 |
| `bilibili.video_info_limit` | `40` | 最多读取多少个视频简介 |
| `bilibili.candidate_limit` / `final_count` | `60` / `10` | 排名候选池 / 每批条数 |
| `history.enabled` | `true` | 是否启用批次延续 |
| `history.state_file` | `~/.agent-plugin-digest/history.json` | 同一用户的跨项目历史 |
| `output.dir` / `filename_pattern` | `output` / 含 `{batch}` | 输出位置与文件名 |
| `output.subtitle_pattern` | `第 {batch} 批 ｜ 共 {total} 条 …` | 文档副标题 |
| `output.intro_min_chars` / `intro_max_chars` | `40` / `120` | 介绍长度告警区间 |
| `output.font` | 按平台自动 | Windows 微软雅黑 / macOS PingFang SC / Linux Noto Sans CJK SC |
| `output.labels` | 中文 | 文档内“项目介绍/项目链接”等标签 |

完整说明与取舍见 [references/selection-criteria.md](references/selection-criteria.md)。
命令行参数（`--min-stars`、`--limit`、`--out-dir`、`--state` 等）会覆盖配置文件。

## 排名规则（批次延续的基础）

批次延续依赖**确定性排序**，脚本已经实现，Agent 不要重排：

- **GitHub**：`sort=stars` 时按星标降序；`sort=updated` 时按最近推送时间降序；
  并列时按 `full_name` 升序。
- **B 站**：`prefer_github_repo=true` 时有仓库的排在前面；同组内按 `pubdate` 降序；
  并列时按 `bvid` 升序。

同一项目在两处出现时，用同一个稳定 key 去重：优先 GitHub 仓库 URL，其次 B 站 BVID。
GitHub 先选；B 站若指向已选仓库则跳过并顺延到下一条。

## 工作流

### 1. GitHub 候选

```bash
python "<skill-dir>/scripts/github_plugins.py" --config my-config.json --out .tmp/github.json
```

### 2. B 站候选

生成全部搜索 URL：

```bash
python "<skill-dir>/scripts/bili_search_url.py" --config my-config.json --json
```

对返回的每个 URL 调用 Firecrawl：

- 工具：`firecrawl_scrape`
- `formats: ["markdown"]`，`onlyMainContent: true`，`waitFor: 4000`，`maxAge: 0`

把每页 markdown 分别保存为 `.tmp/bili_search_1.md`、`.tmp/bili_search_2.md` …，然后：

```bash
python "<skill-dir>/scripts/extract_bvids.py" .tmp/bili_search_1.md .tmp/bili_search_2.md --out .tmp/bvids.json
python "<skill-dir>/scripts/bili_video_info.py" --input .tmp/bvids.json --out .tmp/bili_info.json
python "<skill-dir>/scripts/filter_candidates.py" --input .tmp/bili_info.json --out .tmp/bili_ranked.json
```

`extract_bvids.py` 会按**轮询（round-robin）**合并多个关键词页，避免前几个关键词占满
候选池；`filter_candidates.py` 输出的是**完整排名候选池**（默认 60 条），不是最终批次。
若 `bili_info.json` 的 `errors / count` 超过 `fallback_error_rate`（默认 0.3），
改为对单个视频逐个 `firecrawl_scrape`（`waitFor: 3000`）。

### 3. 选出下一批（关键步骤）

```bash
python "<skill-dir>/scripts/history.py" select \
  --github .tmp/github.json \
  --bilibili .tmp/bili_ranked.json \
  --config my-config.json \
  --out .tmp/next.json
```

输出包含：

- `batch`：本次是第几批；
- `github.items` / `bilibili.items`：按排名选出的下一批；
- `remaining`、`exhausted`：候选池剩余情况。

**不要跳过、替换或重排 `items`**。只按这个顺序为每条写介绍。

### 4. 核验仓库

把 B 站选中条目的 GitHub URL 汇总为 `owner/repo` 列表：

```bash
python "<skill-dir>/scripts/github_plugins.py" --repos "owner/repo1,owner/repo2" --out .tmp/repos.json
```

功能描述必须能在仓库描述、README 或 B 站简介中找到依据，**不要补写未验证的功能**。

### 5. 写入条目文件

按 `next.json` 的顺序写 `.tmp/items.json`，并写入 `batch`：

```json
{
  "title": "GitHub 与 B 站最新 Agent 插件 / Skill 清单",
  "batch": 2,
  "note": "数据来源：GitHub Search API、B 站近期 agent 插件/skill 视频与对应开源仓库；链接截至采集日期可访问。",
  "sections": [
    {"title": "一、GitHub 上最新的 Agent 插件 / Skill（10 条）", "items": [
      {"name": "项目名", "intro": "项目介绍", "url": "https://github.com/owner/repo"}
    ]},
    {"title": "二、B 站近期 Agent 插件 / Skill（10 条）", "items": [
      {"name": "插件名", "intro": "项目介绍", "url": "https://github.com/owner/repo"}
    ]}
  ],
  "footer_note": "B 站条目按视频发布时间与项目对应关系整理，链接优先给出 GitHub 项目页。"
}
```

### 6. 生成 Word

```bash
python "<skill-dir>/scripts/build_docx.py" --input .tmp/items.json --config my-config.json --expected-total 20
```

不传 `--out` 时，按 `output.dir` + `output.filename_pattern` 自动命名（含 `{batch}`）。
目录会自动创建。

### 7. 记录本批（只有成功生成后才执行）

```bash
python "<skill-dir>/scripts/history.py" record \
  --input .tmp/items.json --batch <select 返回的 batch> --config my-config.json
```

- 只有 Word 成功生成后才记录；失败或用户取消时**不要记录**。
- 重复执行 `record` 会因批次不匹配而被拒绝（可用 `--force` 覆盖，通常不需要）。
- 查看状态：`history.py status --config my-config.json`
- 清空历史：`history.py reset --yes --config my-config.json`（仅在用户明确要求时）

### 8. 质检

- 条目数等于 `github.final_count + bilibili.final_count`（默认 20）。
- 本批与历史无重复：`history.py status` 的 `seen_count` 应随批次递增。
- 链接唯一、均为 `http(s)`；抽查 3 条可访问。
- 文档中不出现本机路径、用户名、内网 IP、API Key 或 Cookie。
- 确认没有 DeepSeek 模型章节。

## 再次生成时的行为

1. `history.py select` 读取 `~/.agent-plugin-digest/history.json`；
2. 跳过 `seen` 中的项目，以及本批已选的 GitHub 项目；
3. 按同一排名继续取下一批；
4. Word 生成成功后 `record` 写入本批；
5. 候选池不足时 `exhausted=true`，文档只输出剩余条目，并提示用户是否放宽条件或重置历史。

**不要**用“重新搜索/重新排序”绕过历史；同一用户再次请求时应“往下输出”。
只有用户明确要求“重新生成同一批”时，才使用 `select --no-history`（且不要再 record 重复项）。

## 失败与降级

| 现象 | 处理 |
| --- | --- |
| GitHub 搜索 403 / rate limit | 设置 `GITHUB_TOKEN` 后重跑；脚本会自动等待重置 |
| B 站 API 412 | 脚本带 cookie 引导与重试；仍失败则逐条 `firecrawl_scrape` |
| B 站搜索结果偏少 | 增加 `bilibili.keywords`（如 `MCP 插件`、`AI 编程插件`） |
| Firecrawl 抓取失败 | 重试一次；仍失败则用 B 站公开 API 兜底并在备注中说明 |
| 找不到插件仓库 | 链接可退化为 B 站视频页，并在介绍中写明“视频演示” |
| 候选池耗尽 | 放宽 `min_stars` / `updated_within_days` / 标题过滤，或提高 `candidate_limit` |
| 历史状态损坏 | 删除或重置 `history.state_file`；脚本会报错而不会静默覆盖 |

## 隐私与跨平台约定

- 采集只使用公开页面与公开 API，不读取登录态内容，不保存 Cookie。
- 历史状态只记录公开的标题与 URL，存放在用户主目录，不进入仓库。
- 中间文件放 `.tmp/`，产物放 `output/`（均可配置），不写死绝对路径。
- 文档字体按平台自动选择，也可用 `output.font` 指定。
- 脚本通过 `pathlib` 与 UTF-8 输出处理 Windows/macOS/Linux 差异。
