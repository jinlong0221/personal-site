# AI 记忆备份（longxiong.vip 项目）

本文件夹是龙兄知识库网站（longxiong.vip）的 AI 助手工作记忆备份，
来源：本机 `WorkBuddy/2026-10-25-00-53-17/.workbuddy/memory/` 下的项目记忆。

## 为什么有这个文件夹
AI 助手对本网站的全部认知（站点结构、GitHub 部署机制、缓存戳铁律、
head.html 内联延迟加载器陷阱、审计历史问题登记表等）原本只存在本机工作区。
万一电脑损坏或换机，这些记忆会丢。把它们提交进 GitHub 仓库（云端），
换电脑 clone 下来即可恢复，无需重新教 AI。

## 换电脑后怎么恢复
1. `git clone git@github.com:jinlong0221/personal-site.git`
2. 开新的 WorkBuddy 工作区后，让 AI「读仓库 `.ai-memory/longxiong/` 下的记忆」，
   或把本文件夹内容复制到新工作区的 `.workbuddy/memory/` 下。
3. 像平时一样在对话框说「帮我改网站 xxx」即可，AI 会自动按这些规矩干。

## 重要：本文件夹不会上线
文件夹以 `.` 开头，Hugo 构建时不会复制到 `public/`，线上访客看不到，
仅作为 Git 版本备份存在。

## 维护约定
每次重要会话后，可让 AI 重新执行一次「把本机工作记忆同步进 `.ai-memory/longxiong/`」
并提交推送，保持云端备份与最新认知一致。
