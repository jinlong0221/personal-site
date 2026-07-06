# 龙兄知识库 - Hugo 迁移版

## 迁移说明（2026-07-06）

本仓库已从纯静态 HTML 迁移至 Hugo 静态站点生成器。

### 目录结构
- `content/` — Markdown 内容源文件（未来新增内容放这里）
- `layouts/` — Hugo 模板（navbar/footer/CSS/JS/主题）
- `static/` — 所有静态文件（含原有 149 个 HTML + 资源文件）
- `.github/workflows/deploy.yml` — 自动构建部署到 GitHub Pages

### 工作流程
1. 修改 `static/*.html` → 直接推送到 main
2. 修改 `content/*.md` → 推送到 main，Hugo 自动生成对应 HTML
3. 修改模板 → 推送到 main，Hugo 全站重建
4. GitHub Actions 自动构建并部署

### 本地构建
```bash
~/miniconda3/envs/fooocus/bin/hugo
# 输出到 public/
```

### 注意事项
- 现有 HTML 内容不改动，保持原样
- CSS/JS/图片 保留在 `static/` 目录
- 模板改动会影响所有 Hugo 生成的页面
- `public/` 目录由 Hugo 自动生成，勿手动修改

<!-- Hugo Actions 自动部署测试 10:37 -->
