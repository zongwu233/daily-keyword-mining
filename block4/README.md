# Block 4 — 社区源头聚合器

每天 50 分钟选词 routine 中的 **Block 4（社区源头，15 分钟）** 自动化方案。
抓取多个社区平台的热门内容，聚合为本地 Markdown + HTML 报告。

## 已支持数据源

| 源 | 认证 | 备注 |
|---|---|---|
| Hacker News | 无 | 官方 Firebase API，稳定 |
| Reddit（多 sub） | 无（公开 RSS） | **限流严格**，见下方说明 |
| Product Hunt | Bearer Token | 需注册 PH 应用 |
| YouTube Trending | API Key | 需开启 YouTube Data API v3 |
| Steam 新品 | 无 | 官方 API，稳定 |

## 快速开始

```bash
# 1. 创建配置
cd /home/zw233/project/niche-research
cp block4/config.example.json block4/config.json

# 2. 编辑 config.json，按需填入 token / api_key
#    （不填的源会被自动跳过，不影响其他源）

# 3. 安装依赖
pip install requests feedparser --break-system-packages

# 4. 运行
python3 -m block4.main

# 5. 查看报告
ls digests/
# digest-YYYY-MM-DD.md   — markdown 版
# digest-YYYY-MM-DD.html — 浏览器打开，可点击链接
```

## 配置说明（`block4/config.json`）

```json
{
  "top_n": {
    "hackernews": 20,        // HN Top N
    "producthunt": 10,       // PH Top N
    "youtube": 15,           // YT Top N
    "steam": 15              // Steam Top N
  },
  "reddit": {
    "subreddits": ["all", "InternetIsBeautiful", "SomebodyMakeThis"],
    "top_n_per_sub": 20
  },
  "producthunt": {
    "token": ""              // 留空则跳过
  },
  "youtube": {
    "api_key": "",           // 留空则跳过
    "region_code": "US"      // US / GB / JP / KR ...
  }
}
```

## 获取 token（保姆级步骤）

### Product Hunt Token

PH 的 GraphQL API 需要一个 Bearer Token，5 分钟拿到。

1. **登录**：浏览器打开 https://www.producthunt.com ，没有账号就注册（可用 Google 一键登录）
2. **进入 API 应用管理页**：访问 https://www.producthunt.com/v2/oauth/applications
3. **创建应用**：
   - 点击右上角 **"Add an Application"** 按钮
   - **Name**：随便填，如 `niche-research`
   - **Description**：可空着
   - **Callback URL**：填 `https://localhost`（我们用不上 OAuth 回调，但字段必填）
4. **创建后进入应用详情页**，能看到：
   - `Client ID`（不需要用）
   - `Client Secret`（不需要用）
   - **`Developer Token`**（这是我们要的，一长串字符串）
5. **复制 Developer Token**，填入 config：

```json
{
  "producthunt": {
    "token": "粘贴这里paste_token_here_xxxxxx"
  }
}
```

> 如果应用详情页没直接显示 Developer Token，去应用列表页找 **"Create a token"** 按钮单独生成。

---

### YouTube Data API v3 Key

Google Cloud 控制台稍微繁琐，但全程免费。

1. **进入 Google Cloud Console**：访问 https://console.cloud.google.com/
2. **创建项目**（或复用已有）：
   - 顶部项目下拉 → **"NEW PROJECT"** → Name 随便填，如 `niche-research` → **CREATE**
   - 等几秒创建完成，确认顶部已切到该项目
3. **启用 YouTube Data API v3**：
   - 左侧汉堡菜单 → **APIs & Services** → **Library**
   - 搜索框输入 `YouTube Data API v3` → 点开 → **ENABLE** 按钮（如果显示 ENABLED 跳过）
4. **创建 API Key**：
   - 左侧菜单 → **APIs & Services** → **Credentials**
   - 顶部 **"+ CREATE CREDENTIALS"** → **"API key"**
   - 弹窗显示一长串 key（形如 `AIzaSyB...`），**立即复制**
5. **（推荐）限制 API Key**（防止别人盗用烧你配额）：
   - 在 Credentials 列表里点刚创建的 key 名字
   - **Application restrictions** → 选 `HTTP referrers`（暂时可不限制）
   - **API restrictions** → 选 `Restrict key` → 勾选 `YouTube Data API v3`
   - **SAVE**
6. **填入 config**：

```json
{
  "youtube": {
    "api_key": "AIzaSy粘贴这里xxxxxxxxxxxxx",
    "region_code": "US"
  }
}
```

**配额说明**：免费 10,000 units/天。一次 trending 请求（part=snippet,statistics, maxResults=15）≈ 3 units，每天跑一次能用 3000+ 次，绰绰有余。

---

### 验证 token 是否有效（5 秒）

填完后不要跑完整 main，先用验证脚本单独测两个 token：

```bash
cd /home/zw233/project/niche-research
python3 -m block4.test_tokens
```

预期输出：
```
[PH]  OK  10 items fetched (token valid)
[YT]  OK  15 items fetched (api_key valid)
```

如果看到 FAIL，token 配错了——回到上面步骤检查。

## Reddit 限流说明

Reddit 公开 RSS 反爬严格，单 IP 短时间连续抓取会被 429（连续触发会扩展为 IP 临时黑名单，持续几小时）。

**已实现的应对**：
- 每个 sub 之间 sleep 5 秒
- 429 时退避重试（20s → 40s）
- 单 sub 失败不影响其他 sub

**长期建议**：
- 配置 `subreddits: ["all"]`，只抓 r/all（最热 20 条已经足够）
- 或者注册 Reddit OAuth App，改用官方 API（更稳定，但需改代码）
- 或者添加代理池

## 项目结构

```
block4/
├── __init__.py
├── models.py              # Item / FetchResult 数据结构
├── sources.py             # 5 个源的 fetcher
├── renderer.py            # Markdown + HTML 渲染
├── main.py                # 入口（argparse + 聚合 + 错误隔离）
├── config.example.json    # 配置模板
└── config.json            # 你的实际配置（不要 commit）

digests/
├── digest-YYYY-MM-DD.md
└── digest-YYYY-MM-DD.html
```

## 自动化（可选）

加入 crontab，每天早上 8:00 自动生成报告：

```bash
crontab -e
# 加入：
0 8 * * * cd /home/zw233/project/niche-research && /usr/bin/python3 -m block4.main >> digests/run.log 2>&1
```

## 设计原则

- **单源失败不挂全局**：每个源 try/except 独立，错误记录在报告"源状态"区域
- **零认证优先**：HN / Steam / Reddit 默认不需要任何 key
- **结构化输出**：所有源统一为 `Item` schema，方便后续扩展（如关键词过滤、LLM 评估）
- **可观测**：每个源的抓取状态、错误信息、抓取时间戳都进入报告
