# Block 1 — 趋势扫描聚合器

每天 50 分钟选词 routine 中的 **Block 1（趋势扫描，10 分钟）** 自动化方案。
抓取多源热点信号（文化脉搏 + 开发者脉搏），聚合为本地 Markdown + HTML 报告。

## 已支持数据源

| 源 | 认证 | 信号类型 | 备注 |
|---|---|---|---|
| **Wikipedia Pageviews Top** | 无 | 文化脉搏 | 昨日浏览量 top N，真实用户行为信号 |
| **GitHub Trending** | 无 | 开发者脉搏 | stars today/week，按语言过滤可选 |

### 关于 Google Trends（重要）

原 SOP 计划使用 Google Trends RSS，但 **2026 年 Google 已下线所有公开 RSS 端点**：
- `/trends/trendingsearches/daily/rss` → 404
- `/trends/feeds/dailysearchtrends` → 404
- `/trends/api/dailytrends` → 云服务器 IP 被过滤（仅住宅 IP 可用）
- `pytrends` 库 → 2024-08-10 已归档停更

ExplodingTopics 同样被 Cloudflare 严格封锁（404）。

**替代方案**：Wikipedia Pageviews 提供了"真实用户行为"信号（比 Google Trends 的相对热度更直接），GitHub Trending 对找工具类/SaaS 类选词机会特别准。

## 快速开始

```bash
# 1. 创建配置（零认证，开箱即用）
cd /home/zw233/project/niche-research
cp block1/config.example.json block1/config.json

# 2. 运行
python3 -m block1.main

# 3. 查看报告
ls trends/
# trends-YYYY-MM-DD.md   — markdown 版
# trends-YYYY-MM-DD.html — 浏览器打开，可点击链接
```

无需任何 token / API key。

## 配置说明（`block1/config.json`）

```json
{
  "top_n": {
    "wikipedia": 30,           // Wikipedia Top N（默认 30）
    "github": 25,              // 每个 GitHub 查询的 Top N
    "google_trends": 20        // 每个 Google Trends 地区的 Top N
  },

  "wikipedia": {
    "days_back": 1             // 1=昨天，2=前天（用于补抓）
  },

  "github": {
    "queries": [
      {"since": "daily", "language": ""},
      {"since": "weekly", "language": "python"},
      {"since": "weekly", "language": "typescript"}
    ]
  },

  "google_trends_rss": {
    "enabled": true,
    "geos": ["US", "JP", "GB", "DE", "FR", "IT", "ES"]
  }
}
```

### GitHub 查询参数

- **since**: `daily` / `weekly` / `monthly`
- **language**: 留空 = 所有语言；填具体语言（如 `python` / `typescript` / `rust`）只看该语言

### 添加更多 GitHub 查询

在 `queries` 数组里加条目即可：

```json
"github": {
  "queries": [
    {"since": "daily", "language": ""},
    {"since": "weekly", "language": "python"},
    {"since": "weekly", "language": "typescript"},
    {"since": "weekly", "language": "rust"},
    {"since": "monthly", "language": "go"}
  ]
}
```

## 数据样本

### Wikipedia Top（昨日全球用户行为脉搏）
```
1. Lamine Yamal              views=1,200,352
2. The Odyssey (2026 film)   views=1,108,567
3. 2026 FIFA World Cup       views=815,930
4. Lionel Messi              views=766,741
5. List of FIFA World Cup... views=679,666
```

### GitHub Trending（开发者生态脉搏，带"对你直接相关"信号）
```
[TypeScript] open-seo                    ⭐222 today
  → "Open source alternative to Semrush and Ahrefs"
  → 你做 SEO 选词，这就是直接机会信号
```

## 项目结构

```
block1/
├── __init__.py
├── sources.py              # Wikipedia + GitHub + Google Trends fetcher
├── renderer.py             # Markdown + HTML 渲染
├── main.py                 # 入口（argparse + 聚合 + 错误隔离）
├── config.example.json     # 配置模板
└── config.json             # 你的实际配置

trends/
├── trends-YYYY-MM-DD.md
└── trends-YYYY-MM-DD.html
```

## 与其他 Block 的关系

- **复用 `common.models`**：Item / FetchResult 数据结构完全相同
- **架构一致**：fetcher + renderer + main 三层
- **运行独立**：`python3 -m block1.main`、`python3 -m block3.main`、`python3 -m block4.main` 互不影响
- **报告分开**：`trends/`、`new_domains/`、`digests/` 独立目录

## 自动化（可选）

加入 crontab，每天早上 8:00 自动生成趋势报告：

```bash
crontab -e
# 加入：
0 8 * * * cd /home/zw233/project/niche-research && /usr/bin/python3 -m block1.main >> trends/run.log 2>&1
```

可与 Block 3 / Block 4 串行跑：

```bash
0 8 * * * cd /path && python3 -m block1.main && python3 -m block3.main && python3 -m block4.main
```

## 设计原则

- **零认证**：所有源都不需要 token / API key
- **零封锁风险**：Wikipedia 和 GitHub 都不会因为单 IP 抓取就 429
- **真实信号**：Wikipedia 浏览量 = 用户实际查看行为，比 Google Trends 的相对热度更直接
- **错误隔离**：单源失败不影响其他源
- **可扩展**：在 `queries` 数组加条目即可扩展 GitHub 维度，无需改代码
