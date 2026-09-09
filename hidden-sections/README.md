# 已隐藏板块（沉香鉴别 / 中药材香料）

> 隐藏日期：2026-09-09 ｜ 龙兄要求「暂时不看，需要时再调出来」

这里放的是**从网站上撤下来的板块**，内容一个字没删，只是挪出了构建目录，
所以线上访问会 404，站内任何地方也找不到入口。需要恢复时按下面步骤搬回去即可。

## 目录对应关系（原位置 ← 这里的文件）

| 这里 | 搬回原位置 |
|---|---|
| `static/herbs.html` | `static/herbs.html` |
| `static/herbs/*.html`（9 个：五灵脂、地龙、滑石草、滑石粉、降真香、猫屎咖啡、水蛭、熊胆、地牯牛） | `static/herbs/` |
| `static/herbs-news.json` | `static/herbs-news.json` |
| `content/herbs/_index.md`、`content/herbs/chenxiang.md` | `content/herbs/` |

## 恢复步骤（一次性）

1. 把上表右侧的文件各自搬回原位置：
   ```bash
   git mv hidden-sections/static/herbs.html      static/herbs.html
   git mv hidden-sections/static/herbs-news.json static/herbs-news.json
   git mv hidden-sections/static/herbs           static/herbs
   git mv hidden-sections/content/herbs          content/herbs
   ```

2. 把导航入口加回去：在 `static/*.html`（约 294 个页面）的 `<ul class="nav-links">`
   开头补两行（前缀 `../` 或 `../../` 按页面所在层级）：
   ```html
   <li><a href="herbs/chenxiang.html">沉香鉴别</a></li>
   <li><a href="herbs.html">中药材</a></li>
   ```

3. 首页 `layouts/index.html`：补回「沉香鉴别」「中药材」两张板块卡片。

4. 数据源补回：
   - `data/sitemap_extra.json`：加回 `/herbs.html`（0.9）与 9 个 `/herbs/*.html`（0.7）
   - `static/data/related.json`：加回 `/herbs.html` 及各子页键
   - `static/js/auto_news_loader.js` 的 `PAGE_MAP` 加回 `'herbs': 'herbs-news.json'`
   - `scripts/build_home_feed.py` 加回 `"herbs-news.json": "中药材"`
   - `static/js/daily-pick.js` 加回「沉香鉴别指南」「中药材香料」两条
   - `static/js/daily-item.js` 加回沉香/中药类知识卡

5. 跑 `hugo --gc --minify` 验证，提交推送。

> `static/img/herbs/` 下的图片一直留在原地没动，恢复后直接可用。
