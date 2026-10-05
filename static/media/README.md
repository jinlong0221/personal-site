# static/media —— 站内视频存放目录

## 为什么放这里
`static/` 下的文件会被 Hugo 原样拷贝到产物根路径，所以
`static/media/xxx.mp4` 部署后就是 `https://longxiong.vip/media/xxx.mp4`，
页面里直接 `<video src="/media/xxx.mp4">` 即可。

## 三条硬规矩（不遵守就会踩坑）
1. **单条体积 ≤ 8MB**。GitHub Pages 单文件上限 100MB，但本站 `.git` 已有 391MB，
   视频一旦进去就会永久留在 git 历史里（删文件也去不掉），仓库会很快撑爆。
2. **必须 H.264 + `+faststart`**。`faststart` 把 moov 元数据提到文件头，
   浏览器才能「边下边播」；否则用户要点一下、等整段下完才播。
3. **页面用 `preload="none"` + poster 封面**。否则视频会和其他图片一起抢首屏带宽，
   把整页拖慢（这正是站内一直避开的坑）。

## 用什么工具压
`scripts/make_web_video.sh`（仓库内已带，macOS/Linux 通用，走 Homebrew/miniconda 的 ffmpeg）。
