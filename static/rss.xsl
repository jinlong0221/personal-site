<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom">
  <xsl:output method="html" encoding="UTF-8" indent="yes" doctype-system="about:legacy-compat"/>

  <xsl:template match="/">
    <html lang="zh-CN" data-theme="dark">
      <head>
        <meta charset="UTF-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self' 'sha256-TCireLiEqeKiQGIFN34jYmaEpZpuRJgKauNNRhg1Lxk='; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'self'"/>
        <title>订阅龙兄知识库 - RSS</title>
        <meta name="description" content="订阅龙兄知识库 RSS，获取沉香、中药材、文玩紫砂、特斯拉、射阳民生等更新。"/>
        <link rel="stylesheet" href="/css/style.css?v=20260901"/>
        <link rel="alternate" type="application/rss+xml" title="龙兄知识库 RSS" href="/rss.xml"/>
        <style>
          .rss-wrap{ max-width:760px; margin:0 auto; padding:28px 18px 60px; }
          .rss-hero{ background:var(--card); border:1px solid var(--border); border-radius:16px; padding:28px 24px; margin-bottom:28px; }
          .rss-hero h1{ font-size:1.6rem; margin:0 0 12px; color:var(--gold); }
          .rss-hero p{ color:var(--text-secondary); margin:0 0 20px; line-height:1.7; }
          .rss-url-box{ display:flex; gap:10px; flex-wrap:wrap; align-items:center; background:var(--bg-secondary); border:1px solid var(--border); border-radius:12px; padding:12px 14px; }
          .rss-url-box code{ flex:1; min-width:220px; font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace; font-size:.9rem; color:var(--text); word-break:break-all; }
          .rss-copy-btn{ background:var(--gold); color:#0b0c10; border:0; border-radius:10px; padding:10px 18px; font-weight:700; cursor:pointer; }
          .rss-copy-btn:active{ transform:scale(.97); }
          .rss-help{ margin:24px 0; padding:18px 20px; background:var(--bg-section); border-left:4px solid var(--gold); border-radius:10px; }
          .rss-help h2{ font-size:1.05rem; margin:0 0 10px; color:var(--text); }
          .rss-help ul{ margin:0; padding-left:20px; color:var(--text-secondary); line-height:1.8; }
          .rss-feed-title{ font-size:1.25rem; margin:36px 0 16px; color:var(--text); }
          .rss-list{ display:flex; flex-direction:column; gap:16px; }
          .rss-item{ background:var(--card); border:1px solid var(--border); border-radius:14px; padding:18px 20px; transition:border-color .2s; }
          .rss-item:hover{ border-color:var(--gold); }
          .rss-item-title{ font-size:1.05rem; font-weight:700; margin:0 0 8px; }
          .rss-item-title a{ color:var(--text); text-decoration:none; }
          .rss-item-title a:hover{ color:var(--gold); }
          .rss-item-meta{ font-size:.82rem; color:var(--text-muted); margin-bottom:10px; }
          .rss-item-desc{ color:var(--text-secondary); font-size:.92rem; line-height:1.7; margin:0; }
          .rss-empty{ color:var(--text-muted); text-align:center; padding:40px 0; }
        </style>
      </head>
      <body>
        <div class="rss-wrap">
          <nav class="breadcrumb" aria-label="面包屑">
            <a href="/">首页</a>
            <span>/</span>
            <span>RSS 订阅</span>
          </nav>

          <section class="rss-hero">
            <h1>📰 订阅龙兄知识库</h1>
            <p>龙兄知识库 RSS 订阅源，涵盖沉香鉴别、中药材、文玩紫砂、特斯拉、射阳本地民生等实用图文。把下方地址复制到你喜欢的 RSS 阅读器即可订阅。</p>
            <div class="rss-url-box">
              <code id="rssUrl">https://longxiong.vip/rss.xml</code>
              <button class="rss-copy-btn" id="rssCopyBtn">复制地址</button>
            </div>
          </section>

          <section class="rss-help">
            <h2>如何订阅？</h2>
            <ul>
              <li>点击上方「复制地址」按钮。</li>
              <li>打开你的 RSS 阅读器（如 Feedly、Inoreader、Reeder、NetNewsWire、Cubox 等）。</li>
              <li>选择「添加订阅源」并粘贴上面的地址。</li>
            </ul>
          </section>

          <h2 class="rss-feed-title">最新文章</h2>
          <div class="rss-list">
            <xsl:choose>
              <xsl:when test="count(/rss/channel/item) = 0">
                <p class="rss-empty">暂无文章。</p>
              </xsl:when>
              <xsl:otherwise>
                <xsl:for-each select="/rss/channel/item">
                  <article class="rss-item">
                    <h3 class="rss-item-title">
                      <a target="_blank" rel="noopener">
                        <xsl:attribute name="href">
                          <xsl:value-of select="link"/>
                        </xsl:attribute>
                        <xsl:value-of select="title"/>
                      </a>
                    </h3>
                    <div class="rss-item-meta">
                      <xsl:if test="category">
                        <span class="tag"><xsl:value-of select="category"/></span>
                        <span> · </span>
                      </xsl:if>
                      <time><xsl:value-of select="pubDate"/></time>
                    </div>
                    <p class="rss-item-desc"><xsl:value-of select="description"/></p>
                  </article>
                </xsl:for-each>
              </xsl:otherwise>
            </xsl:choose>
          </div>
        </div>

        <script>
          function copyRssUrl(){
            const url = document.getElementById('rssUrl').textContent;
            if (navigator.clipboard) {
              navigator.clipboard.writeText(url).then(function(){
                const btn = document.querySelector('.rss-copy-btn');
                const old = btn.textContent;
                btn.textContent = '已复制';
                setTimeout(function(){ btn.textContent = old; }, 1500);
              });
            } else {
              const ta = document.createElement('textarea');
              ta.value = url;
              document.body.appendChild(ta);
              ta.select();
              document.execCommand('copy');
              document.body.removeChild(ta);
              const btn = document.querySelector('.rss-copy-btn');
              const old = btn.textContent;
              btn.textContent = '已复制';
              setTimeout(function(){ btn.textContent = old; }, 1500);
            }
          }
          document.getElementById('rssCopyBtn').addEventListener('click', copyRssUrl);
        </script>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
