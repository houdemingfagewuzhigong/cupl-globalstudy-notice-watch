# 法大国际合作通知公告观察站

[English README](README.md)

这是一个非官方的中国政法大学国际合作与交流相关公开通知公告每日归档项目，面向需要跟踪出国境项目、交流项目、通知公告和历史数据的学生、教师和项目团队。

![看板示意](assets/demo.svg)

## 项目定位

- 目标站点：`https://globalstudy.cupl.edu.cn/`
- 通知公告页：`https://globalstudy.cupl.edu.cn/news`
- 从公开前端脚本反查到的官方接口：`https://globalstudy.cupl.edu.cn/api/news/query`
- 覆盖栏目：通知公告、新闻动态

当前网络环境下，目标站点可能返回站点防护 HTML，而不是接口 JSON。爬虫会把诊断信息写入 `data/meta.json`，并保留已有历史数据；一旦运行环境可正常访问官方 API，定时任务会自动追加新公告。

## 快速开始

```bash
python3 scraper.py 3
python3 -m http.server 8000
```

然后打开 `http://localhost:8000` 查看静态看板。

## 数据结构

- `data/notices.json`：合并后的历史公告。
- `data/notices.csv`：便于 Excel/WPS 打开的 CSV。
- `data/history/YYYY-MM-DD.json`：每天本次运行新抓到的数据。
- `data/meta.json`：更新时间、来源 URL、总量、诊断信息和免责声明。

每条公告字段包括：

- `id`
- `title`
- `date`
- `url`
- `summary`
- `section`
- `source_url`
- `first_seen_at`
- `last_seen_at`

## 定时更新

`.github/workflows/update.yml` 会每天自动运行：

1. 安装 Python。
2. 执行 `python3 scraper.py 3`。
3. 如果 `data/` 有变化，自动提交到仓库。

## 前端看板

`index.html`、`styles.css`、`app.js` 构成一个可直接部署到 GitHub Pages、Vercel 或 Netlify 的静态看板，支持：

- 最新公告展示
- 关键词搜索
- 栏目筛选
- 统计卡片
- JSON / CSV 导出

## 申报材料

`docs/project_proposal.docx` 是使用 `python-docx` 生成的项目说明/创新创业申报材料，包含项目背景、目标用户、技术路线、数据结构、合规说明、应用价值和后续扩展。

## 免责声明

本项目仅归档公开网页信息，不绕过访问控制，不抓取个人隐私数据，不代表中国政法大学官方。公告内容以学校官方页面为准。

## License

MIT
