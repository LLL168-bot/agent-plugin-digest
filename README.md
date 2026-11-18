# agent-plugin-digest

A Claude Code plugin (skill) that collects the latest **agent plugins and skills from
GitHub and Bilibili**, ranks them with configurable criteria, verifies project links, and
renders a Word digest in the fixed format **name + introduction + link**.

- **Batch continuation**: a second run skips what was already delivered and outputs the
  next items in the same deterministic ranking.
- Works on Windows, macOS, and Linux.

## Features

- Configurable GitHub topics, star threshold, recency window, keyword filters, candidate
  pool, and per-batch count.
- Multiple Bilibili search keywords (defaults: `agent 插件`, `agent skill`,
  `Claude Code 插件`, `dsh 插件`); results are merged and deduplicated by BVID.
- Extracts GitHub project links from video descriptions and verifies them against the
  GitHub API.
- Deterministic ranking; the agent writes introductions but does not reorder items.
- Per-user history (`~/.agent-plugin-digest/history.json` by default) so later batches
  continue down the ranking instead of repeating earlier items.
- Produces a `.docx` with clickable hyperlinks and platform-appropriate CJK fonts.

## Install

Add this repository as a local marketplace, then install the plugin:

```text
/plugin marketplace add <path-to-this-repo>
/plugin install agent-plugin-digest@agent-plugin-digest-marketplace
```

For a one-session trial without installing:

```bash
claude --plugin-dir <path-to-this-repo>/plugins/agent-plugin-digest
```

Reload with `/reload-plugins` or start a new session if the skill does not appear.
The installed skill is namespaced as `/agent-plugin-digest:agent-plugin-digest`.

## Requirements

- Claude Code with the **Firecrawl MCP** connected (`firecrawl_search`,
  `firecrawl_scrape`). Bilibili search pages require browser rendering.
- Python 3.10+ and `python-docx`:

  ```bash
  python -c "import docx" || pip install python-docx
  ```

  On macOS/Linux use `python3` and `pip3`.
- Optional: `GITHUB_TOKEN` to raise the GitHub search rate limit.

## Usage

Ask Claude Code:

```text
爬取最新的 agent 插件和 skill，生成 Word 清单
```

Default output: 20 items (10 GitHub + 10 Bilibili) in `output/`, created automatically.
The filename and subtitle include the batch number.

## Batch continuation

- First run: items ranked 1–10 from each source.
- Second run by the same user: items ranked 11–20, skipping anything already recorded.
- Stable keys are the GitHub repository (`owner/repo`) or the Bilibili BVID; a repository
  already used in the GitHub section is skipped in the Bilibili section.
- History is written only after a Word document is successfully generated.
- Inspect or reset:

  ```bash
  python "<skill-dir>/scripts/history.py" status
  python "<skill-dir>/scripts/history.py" reset --yes   # only on explicit request
  ```

## Configuration

Defaults live in
[`plugins/agent-plugin-digest/skills/agent-plugin-digest/config/default.json`](plugins/agent-plugin-digest/skills/agent-plugin-digest/config/default.json).
Override only what you need:

```json
{
  "github": {"min_stars": 200, "updated_within_days": 90, "candidate_limit": 80},
  "bilibili": {
    "keywords": ["agent 插件", "agent skill", "MCP 插件"],
    "candidate_limit": 80,
    "video_info_limit": 60
  },
  "history": {"state_file": "~/.agent-plugin-digest/history.json"},
  "output": {"dir": "reports"}
}
```

Every option and its trade-offs are documented in
[`selection-criteria.md`](plugins/agent-plugin-digest/skills/agent-plugin-digest/references/selection-criteria.md).
Command-line flags (`--min-stars`, `--limit`, `--out-dir`, `--state`, …) override the
config file.

## Project layout

```text
.claude-plugin/marketplace.json          local marketplace
plugins/agent-plugin-digest/
├── .claude-plugin/plugin.json           plugin manifest + icon
├── README.md / LICENSE
└── skills/agent-plugin-digest/
    ├── SKILL.md
    ├── config/default.json
    ├── references/{selection-criteria,landscape}.md
    └── scripts/*.py
tests/                                     CI smoke tests
```

## Privacy

- Only public pages and public APIs are used.
- No cookies are persisted; the Bilibili helper bootstraps an anonymous in-memory
  session for anti-bot compatibility.
- History contains only public titles and URLs.
- Intermediate files go to `.tmp/`; outputs go to `output/` (both configurable).
- Scripts embed no absolute paths or environment-specific values.

## Similar projects

The landscape review is in
[`landscape.md`](plugins/agent-plugin-digest/skills/agent-plugin-digest/references/landscape.md).
No exact equivalent was found; the closest is Firecrawl's `last30flames`.

## License

MIT. See [LICENSE](LICENSE).

---

## 中文说明

这是一个 Claude Code 插件：采集 **GitHub 与 B 站**上最新的 **Agent 插件 / Skill**，按
可配置条件排序、核验链接，输出“项目名 + 项目介绍 + 项目链接”的 Word 清单。

默认每批 20 条，支持多关键词 B 站检索与**批次延续**：同一用户再次生成时自动跳过已交付
项目，按同一排名继续输出下一批。历史文件默认在 `~/.agent-plugin-digest/history.json`，
可在配置中修改或重置。

安装：

```text
/plugin marketplace add <本仓库路径>
/plugin install agent-plugin-digest@agent-plugin-digest-marketplace
```
