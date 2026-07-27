# Block 3 — 新注册域名反推

每天 routine 中的 **Block 3（新注册域名反推，5 分钟）** 自动化方案。

从 WhoisDS 公开的 Newly Registered Domains 日报抓取新注册域名，按 TLD、长度、商业意图词等启发式规则生成候选榜单。同分域名会按首字母轮转输出，避免报告前几百条都被 a/b/c 开头域名占满。

## 快速开始

```bash
python3 -m block3.main
```

输出：

```bash
new_domains/new-domains-YYYY-MM-DD.md
new_domains/new-domains-YYYY-MM-DD.html
```

## 配置

复制并调整：

```bash
cp block3/config.example.json block3/config.json
```

字段：

- `top_n.new_domains`：输出候选数量，默认 200
- `new_domains.max_days`：读取最近几个 WhoisDS 免费日报链接
- `new_domains.sample_limit`：最多抽样多少域名
- `new_domains.min_score`：最低信号分

## 边界

这里的 `signal` 不是真实流量，只是新注册域名的候选优先级。真实 “Fastest Growing” 仍需要 SimilarWeb、Cloudflare Radar、Tranco、CrUX 或 clickstream 类数据验证。
