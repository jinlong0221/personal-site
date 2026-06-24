#!/usr/bin/env python3
"""Batch 1: 经典壶型系列 8 件 → pages/zisha/detail-*.html"""
import re, os

SITE = '/Users/chenjinlong/陈金龙/代码与脚本/个人知识网站'
os.chdir(SITE)

with open('zisha.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ── 数据：从 zisha.html 中精确提取这 8 件作品 ──────────────────
works = [
    {
        'file': 'pages/zisha/detail-gujing-ziqidonglai.html',
        'name': '🏆 紫气东来',
        'name_plain': '紫气东来',
        'capacity': '430ml',
        'clay': '原矿黄金段泥',
        'series': '经典壶型·生肖系列',
        'img': 'img/zisha/zisha_p24_0.webp',
        'caption': '紫气东来 | 金奖作品',
        'tags': ['中誉杯金奖', '生肖限量', '龙年纪念'],
        'short_desc': '吴昊天先生原创设计首款生肖作品，荣获「中誉杯」工艺美术创新作品大赛金奖。壶身为汉时瓦缸，壶钮为汉时瓦片浮雕祥云，壶嘴壶把为东方巨龙，象征祥瑞之气出自东方。',
        'concept': '「紫气东来」是吴昊天先生为2024龙年精心创作的生肖纪念壶，荣获「中誉杯」工艺美术创新作品大赛金奖。\n\n设计理念：壶身借鉴汉代瓦缸造型，古朴厚重；壶钮以汉代瓦片浮雕祥云纹，寓意风调雨顺；壶嘴与壶把均塑为东方巨龙形象，龙首高昂，气势磅礴。整体设计将汉文化图腾与紫砂壶艺完美融合。\n\n泥料采用黄龙山原矿黄金段泥，色泽温润如金。壶容量430ml，适合三五知己品茗赏壶。',
        'specs': {'容量': '430ml', '泥料': '原矿黄金段泥', '烧制': '1300°C 高温', '工艺': '全手工制作', '系列': '经典壶型·生肖系列', '获奖': '「中誉杯」工艺美术创新作品大赛金奖'},
        'related': [
            ('detail-gujing-guoqiaobianfu.html', '过桥扁腹', 'img/zisha/zisha_p23_0.webp'),
        ]
    },
    {
        'file': 'pages/zisha/detail-gujing-guoqiaobianfu.html',
        'name': '过桥扁腹',
        'name_plain': '过桥扁腹',
        'capacity': '250ml',
        'clay': '原矿紫泥',
        'series': '经典壶型系列',
        'img': 'img/zisha/zisha_p23_0.webp',
        'caption': '过桥扁腹',
        'tags': ['清末经典', '黄玉麟之作', '全手工'],
        'short_desc': '清末制壶大家黄玉麟经典之作，由仿古壶演变而来。壶体扁圆不塌，转折弧线优雅精当，短弯流嘴出水有力，玉环圆把飘逸自如，体现紫砂艺术「圆、稳、匀、正」美学意蕴。',
        'concept': '「过桥扁腹」源自清末制壶大家黄玉麟的经典造型，由仿古壶演变而来。\n\n壶体扁圆而不塌，转折弧线优雅精当，体现了紫砂艺术「圆、稳、匀、正」的核心美学意蕴。短弯流嘴出水有力，玉环圆把飘逸自如，拿捏舒适。\n\n选用黄龙山原矿紫泥，泥质细腻温润，经长期泡养后色泽愈发沉稳深邃，是实用与收藏兼备的佳品。',
        'specs': {'容量': '250ml', '泥料': '原矿紫泥', '烧制': '1180°C 中温', '工艺': '全手工拍打成型', '系列': '经典壶型系列', '渊源': '清末黄玉麟经典造型'},
        'related': [
            ('detail-gujing-ziqidonglai.html', '🏆 紫气东来', 'img/zisha/zisha_p24_0.webp'),
            ('detail-gujing-daobaoxishi.html', '倒把西施', 'img/zisha/zisha_p24_0.webp'),
        ]
    },
    {
        'file': 'pages/zisha/detail-gujing-daobaoxishi.html',
        'name': '倒把西施',
        'name_plain': '倒把西施',
        'capacity': '220ml',
        'clay': '原矿降坡泥',
        'series': '经典壶型系列',
        'img': 'img/zisha/zisha_p24_0.webp',
        'caption': '倒把西施 | 原矿降坡泥 220ml',
        'tags': ['西施壶', '倒把设计', '降坡泥'],
        'short_desc': '壶身圆润，截盖设计、短嘴、倒把把手，构成西施壶特殊审美效果，成为紫砂壶经典。选用宜兴黄龙山珍贵稀有红降坡泥制作。',
        'concept': '西施壶是紫砂壶六大经典造型之一，以古代美女西施为名，壶身圆润如乳，娇憨可爱。\n\n此款「倒把西施」在传统西施壶基础上改良：截盖设计使壶盖与壶身浑然一体；短弯嘴出水爽利；倒把把手符合人体工学，单手执壶极为舒适。\n\n泥料选用黄龙山珍贵稀有的红降坡泥，此泥料存世量极少，烧成后色泽红润中带黄斑点，古朴自然，泡养后愈发温润可人。',
        'specs': {'容量': '220ml', '泥料': '原矿降坡泥', '烧制': '1180°C 中温', '工艺': '全手工', '系列': '经典壶型系列', '特点': '倒把设计，执壶舒适'},
        'related': [
            ('detail-gujing-guoqiaobianfu.html', '过桥扁腹', 'img/zisha/zisha_p23_0.webp'),
            ('detail-gujing-pinggailianzi.html', '平盖莲子', 'img/zisha/zisha_p25_0.webp'),
        ]
    },
    {
        'file': 'pages/zisha/detail-gujing-pinggailianzi.html',
        'name': '平盖莲子',
        'name_plain': '平盖莲子',
        'capacity': '300ml',
        'clay': '原矿红皮龙',
        'series': '经典壶型系列',
        'img': 'img/zisha/zisha_p25_0.webp',
        'caption': '平盖莲子 | 原矿红皮龙 300ml',
        'tags': ['莲子造型', '平盖设计', '吉祥寓意'],
        'short_desc': '造型源于莲子，象征纯洁高雅。造型古朴大方，婉约俏丽，壶身浑圆饱满，曲线委婉动人。蕴含「连生贵子」吉祥寓意。',
        'concept': '「平盖莲子」造型源于自然界的莲子，象征纯洁高雅、连生贵子之美意。\n\n壶身浑圆饱满，曲线委婉动人；平盖设计稳重大方，与壶身圆润线条相呼应。三弯流嘴出水柔顺，耳形把拿捏舒适。整体造型古朴大方，婉约俏丽，兼具实用性与观赏性。\n\n泥料采用黄龙山原矿红皮龙，泥色红润鲜亮，透气性佳，特别适合冲泡普洱茶与黑茶。',
        'specs': {'容量': '300ml', '泥料': '原矿红皮龙', '烧制': '1180°C 中温', '工艺': '全手工', '系列': '经典壶型系列', '寓意': '连生贵子，纯洁高雅'},
        'related': [
            ('detail-gujing-daobaoxishi.html', '倒把西施', 'img/zisha/zisha_p24_0.webp'),
            ('detail-gujing-rongtian.html', '容天', 'img/zisha/zisha_p26_0.webp'),
        ]
    },
    {
        'file': 'pages/zisha/detail-gujing-rongtian.html',
        'name': '容天',
        'name_plain': '容天',
        'capacity': '200ml',
        'clay': '原矿清水泥',
        'series': '经典壶型系列',
        'img': 'img/zisha/zisha_p26_0.webp',
        'caption': '容天 | 原矿清水泥 200ml',
        'tags': ['佛教题材', '大肚罗汉', '包容'],
        'short_desc': '寓意「大肚能容，容天下难容之事」，设计灵感源自佛教大肚罗汉，象征宽容大度和包容一切。壶型饱满圆润，线条流畅，富有哲理。',
        'concept': '「容天」壶的设计灵感源自佛教大肚罗汉（弥勒佛），寓意「大肚能容，容天下难容之事」，象征宽容大度和包容一切的胸怀。\n\n壶型饱满圆润，线条流畅自然，壶盖微隆与壶身浑然一体。短流嘴出水有力，圆把握感舒适。整体造型富有哲理意蕴，品茗之余更能感悟人生智慧。\n\n泥料选用黄龙山原矿清水泥，泥色紫红纯正，质感细腻，经泡养后逐渐呈现出温润如玉的包浆效果。',
        'specs': {'容量': '200ml', '泥料': '原矿清水泥', '烧制': '1180°C 中温', '工艺': '全手工', '系列': '经典壶型系列', '寓意': '大肚能容，宽容大度'},
        'related': [
            ('detail-gujing-pinggailianzi.html', '平盖莲子', 'img/zisha/zisha_p25_0.webp'),
            ('detail-gujing-fanggu.html', '仿古', 'img/zisha/zisha_p26_0.webp'),
        ]
    },
    {
        'file': 'pages/zisha/detail-gujing-fanggu.html',
        'name': '仿古',
        'name_plain': '仿古',
        'capacity': '300ml',
        'clay': '原矿紫泥',
        'series': '经典壶型系列',
        'img': 'img/zisha/zisha_p26_0.webp',
        'caption': '仿古 | 原矿紫泥 300ml',
        'tags': ['仿古青铜器', '经典造型', '大气'],
        'short_desc': '模仿古代青铜器造型，形态和功能完美结合，「藏而不泄」是为「宝」。象征对功名事业的追求，一鼓作气奋发向上。',
        'concept': '「仿古」壶造型模仿古代青铜器，将上古礼器的庄重与紫砂壶的实用完美融合，是紫砂六大经典造型之一。\n\n壶身扁圆饱满，壶颈收敛，平盖配珠钮，一弯流嘴短促有力，圈把圆润自然。整体气势沉稳大气，「藏而不泄」的造型哲学，寓意内敛含蓄、厚积薄发。\n\n泥料采用黄龙山原矿紫泥，泥质细腻温润，烧成后呈深紫色，古朴端庄。此壶适合冲泡普洱、黑茶等需要高温激发香气的茶类。',
        'specs': {'容量': '300ml', '泥料': '原矿紫泥', '烧制': '1180°C 中温', '工艺': '全手工', '系列': '经典壶型系列', '寓意': '仿古礼器，厚积薄发'},
        'related': [
            ('detail-gujing-rongtian.html', '容天', 'img/zisha/zisha_p26_0.webp'),
            ('detail-gujing-dahengduozhi-xiao.html', '大亨掇只（小）', 'img/zisha/zisha_p27_0.webp'),
        ]
    },
    {
        'file': 'pages/zisha/detail-gujing-dahengduozhi-xiao.html',
        'name': '大亨掇只（小）',
        'name_plain': '大亨掇只（小）',
        'capacity': '220ml',
        'clay': '原矿天星泥',
        'series': '经典壶型系列',
        'img': 'img/zisha/zisha_p27_0.webp',
        'caption': '大亨掇只（小）| 原矿天星泥 220ml',
        'tags': ['邵大亨之作', '千金壶王', '天星泥'],
        'short_desc': '清代制壶名家邵大亨代表作品，被称为「千金壶王」。选用黄龙山三种以上原矿泥料科学配比全手工制作，经柴窑高温烧制，砂粒感强俗称「天星泥」，双重透气性。',
        'concept': '「大亨掇只」是清代制壶名家邵大亨的代表作品，被誉为「千金壶王」，是紫砂史上最具传奇色彩的壶型之一。\n\n此壶选用黄龙山三种以上原矿泥料科学配比，经全手工拍打成型，再经柴窑高温烧制。泥料中因含多种矿料，烧成后表面砂粒感强，俗称「天星泥」，具有双重透气性，泡茶效果极佳。\n\n掇只壶型简洁大方，壶身圆润饱满，短弯嘴出水爽利，圈把圆润有力。邵大亨之作存世极少，此复刻版力求还原大家神韵。',
        'specs': {'容量': '220ml', '泥料': '原矿天星泥（多矿配比）', '烧制': '柴窑高温', '工艺': '全手工拍打成型', '系列': '经典壶型系列', '渊源': '清代邵大亨「千金壶王」'},
        'related': [
            ('detail-gujing-fanggu.html', '仿古', 'img/zisha/zisha_p26_0.webp'),
            ('detail-gujing-dahengduozhi-da.html', '大亨掇只（大）', 'img/zisha/zisha_p29_0.webp'),
        ]
    },
    {
        'file': 'pages/zisha/detail-gujing-dahengduozhi-da.html',
        'name': '大亨掇只（大）',
        'name_plain': '大亨掇只（大）',
        'capacity': '380ml',
        'clay': '原矿天星泥',
        'series': '经典壶型系列',
        'img': 'img/zisha/zisha_p29_0.webp',
        'caption': '大亨掇只（大）| 原矿天星泥 380ml',
        'tags': ['邵大亨之作', '千金壶王', '大容量'],
        'short_desc': '千金壶王大版，380ml容量。诠释儒家用世、道家清净和佛家圆融，简朴无华、素净端庄。',
        'concept': '「大亨掇只（大）」是邵大亨「千金壶王」的大容量版本，380ml的大容量为多人品茗而设计。\n\n大亨掇只的造型哲学诠释了儒家用世、道家清净和佛家圆融的思想境界：壶身圆润而不臃肿，线条简朴无华，素净端庄，没有繁复装饰，却自有一种内在的力量。\n\n泥料同样采用黄龙山多矿配比天星泥，经柴窑高温烧制，表面星点密布，古朴天然。大容量设计适合茶席多人共享，是收藏与实用兼备的佳作。',
        'specs': {'容量': '380ml', '泥料': '原矿天星泥（多矿配比）', '烧制': '柴窑高温', '工艺': '全手工拍打成型', '系列': '经典壶型系列', '特点': '大容量，多人品茗'},
        'related': [
            ('detail-gujing-dahengduozhi-xiao.html', '大亨掇只（小）', 'img/zisha/zisha_p27_0.webp'),
            ('detail-gujing-ziqidonglai.html', '🏆 紫气东来', 'img/zisha/zisha_p24_0.webp'),
        ]
    },
]

# ── 生成详情页 ────────────────────────────────────────────────────────
TEMPLATE = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{desc}">
<script>(function(){{try{{var t=localStorage.getItem('theme');if(t==='light'||t==='dark'){{document.documentElement.setAttribute('data-theme',t)}}else{{var h=new Date().getHours();document.documentElement.setAttribute('data-theme',(h>=6&&h<18)?'light':'dark')}}}}catch(e){{}})();}}</script>
<link rel="stylesheet" href="../css/style.css">
<style>
:root{{--zs-brown:#6D4C41;--zs-gold:#BCAAA4;--zs-dark:#3E2723;--zs-light:#EFEBE9;}}
[data-theme="light"]{{--bg:#FAF5F0;--card:#FFFCF8;--text:#3E2723;--muted:#8D6E63;--border:#D7CCC8;}}
[data-theme="dark"]{{--bg:#1A1210;--card:#2C1E18;--text:#EFEBE9;--muted:#A1887F;--border:#4E342E;}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;}}
.navbar{{background:var(--card);border-bottom:1px solid var(--border);padding:14px 24px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:100;box-shadow:0 1px 4px rgba(0,0,0,0.06);}}
.logo{{font-weight:700;font-size:1.3rem;color:var(--text);text-decoration:none;}}
.nav-links{{display:flex;gap:16px;list-style:none;margin:0 0 0 auto;padding:0;}}
.nav-links a{{color:var(--muted);text-decoration:none;font-size:1.1rem;}}
.nav-links a:hover{{color:var(--text);}}
.breadcrumb{{max-width:900px;margin:20px auto 0;padding:0 24px;font-size:1.05rem;color:var(--muted);}}
.breadcrumb a{{color:var(--muted);text-decoration:none;}}
.breadcrumb a:hover{{color:var(--text);}}
.detail-hero{{max-width:900px;margin:24px auto;padding:0 24px;display:grid;grid-template-columns:1fr 1fr;gap:32px;align-items:start;}}
@media(max-width:700px){{.detail-hero{{grid-template-columns:1fr;}}}}
.detail-img-wrap{{border-radius:12px;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,0.15);cursor:zoom-in;}}
.detail-img-wrap img{{width:100%;display:block;}}
.detail-info{{}}
.detail-title{{font-size:2rem;font-weight:700;color:var(--zs-brown);margin:0 0 12px;letter-spacing:2px;line-height:1.3;}}
.detail-meta{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;}}
.meta-pill{{background:var(--card);border:1px solid var(--border);color:var(--muted);padding:5px 14px;border-radius:20px;font-size:1.05rem;}}
.detail-tags{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;}}
.tag{{background:var(--zs-brown);color:#fff;padding:4px 12px;border-radius:6px;font-size:0.95rem;}}
.detail-section{{max-width:900px;margin:0 auto;padding:0 24px;}}
.section-label{{font-size:1.15rem;color:var(--zs-brown);letter-spacing:2px;margin:28px 0 14px;font-weight:600;border-left:4px solid var(--zs-brown);padding-left:12px;}}
.detail-desc{{font-size:1.15rem;color:var(--text);line-height:1.9;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px 24px;margin-bottom:16px;}}
.detail-desc p{{margin:0 0 14px;text-indent:2em;}}
.detail-desc p:last-child{{margin-bottom:0;}}
.spec-table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden;margin-bottom:24px;}}
.spec-table th,.spec-table td{{padding:12px 18px;text-align:left;border-bottom:1px solid var(--border);font-size:1.08rem;}}
.spec-table th{{background:var(--zs-brown);color:#fff;width:120px;}}
.spec-table td{{color:var(--text);}}
.related-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:16px;margin-bottom:40px;}}
.related-card{{display:block;text-decoration:none;background:var(--card);border:1px solid var(--border);border-radius:10px;overflow:hidden;transition:transform 0.2s,box-shadow 0.2s;}}
.related-card:hover{{transform:translateY(-3px);box-shadow:0 6px 20px rgba(0,0,0,0.12);}}
.related-card img{{width:100%;height:120px;object-fit:cover;display:block;}}
.related-card span{{display:block;padding:10px 12px;color:var(--text);font-size:1.05rem;font-weight:500;}}
</style>
</head>
<body>
  <div class="navbar">
    <a href="../index.html" class="logo">龙兄知识库</a>
    <span id="navClock" class="nav-clock"></span>
    <span class="nav-weather" id="navWeather" onclick="location.href='../sheyang.html'">🌤️</span>
    <ul class="nav-links">
      <li><a href="../agarwood.html">沉香鉴别</a></li>
      <li><a href="../herbs.html">中药材</a></li>
      <li><a href="zisha.html">紫砂艺术</a></li>
      <li><a href="../tesla.html">特斯拉</a></li>
    </ul>
  </div>

  <div class="breadcrumb">
    <a href="../index.html">首页</a> › <a href="zisha.html">紫砂艺术</a> › <span>{name_plain}</span>
  </div>

  <div class="detail-hero">
    <div class="detail-img-wrap" onclick="openLightbox(this)">
      <img src="../{img}" alt="{caption}">
    </div>
    <div class="detail-info">
      <h1 class="detail-title">{name}</h1>
      <div class="detail-meta">
        <span class="meta-pill">🫖 容量：{capacity}</span>
        <span class="meta-pill">🏺 泥料：{clay}</span>
        <span class="meta-pill">📁 系列：{series}</span>
      </div>
      <div class="detail-tags">
        {tags_html}
      </div>
    </div>
  </div>

  <div class="detail-section">
    <div class="section-label">作品简介</div>
    <div class="detail-desc"><p>{short_desc}</p></div>

    <div class="section-label">设计理念</div>
    <div class="detail-desc">
      {concept_html}
    </div>

    <div class="section-label">规格参数</div>
    <table class="spec-table">
      {specs_html}
    </table>

    <div class="section-label">同系列作品</div>
    <div class="related-grid">
      {related_html}
    </div>
  </div>

<script>
(function(){{
  function updateClock(){{var el=document.getElementById('navClock');if(el)el.textContent=new Date().toLocaleTimeString('zh-CN',{{hour:'2-digit',minute:'2-digit'}});}}
  updateClock();setInterval(updateClock,1000);
}})();
function openLightbox(el){{
  var src=el.querySelector('img').src;
  var ov=document.createElement('div');
  ov.style='position:fixed;inset:0;background:rgba(0,0,0,0.93);z-index:9999;display:flex;justify-content:center;align-items:center;cursor:pointer';
  ov.innerHTML='<img src="'+src+'" style="max-width:90%;max-height:90vh;border-radius:8px;object-fit:contain;" />';
  ov.onclick=function(){{document.body.removeChild(ov);}};
  document.body.appendChild(ov);
}}
</script>
</body>
</html>'''

os.makedirs('pages/zisha', exist_ok=True)

for w in works:
    tags_html = ''.join('<span class="tag">%s</span>' % t for t in w['tags'])
    concept_paras = ''.join('<p>%s</p>' % p for p in w['concept'].split('\n') if p.strip())
    specs_html = ''.join('<tr><th>%s</th><td>%s</td></tr>' % (k, v) for k, v in w['specs'].items())
    related_html = ''.join(
        '<a class="related-card" href="%s"><img src="../%s" alt="%s"><span>%s</span></a>' % (rf, rim, rn, rn)
        for rf, rn, rim in w['related']
    )
    page = TEMPLATE.format(
        title='%s | 紫砂艺术 | 龙兄知识库' % w['name'],
        desc=w['short_desc'][:80],
        name=w['name'],
        name_plain=w['name_plain'],
        img=w['img'],
        caption=w['caption'],
        capacity=w['capacity'],
        clay=w['clay'],
        series=w['series'],
        tags_html=tags_html,
        short_desc=w['short_desc'],
        concept_html=concept_paras,
        specs_html=specs_html,
        related_html=related_html,
    )
    with open(w['file'], 'w', encoding='utf-8') as f:
        f.write(page)
    print('✅ %s' % w['file'])

# ── 更新 zisha.html 中这 8 件作品的 href ─────────────────────────
link_map = {w['name']: '../' + w['file'] for w in works}
link_map.update({w['name_plain']: '../' + w['file'] for w in works})

def replace_links(m):
    card = m.group(0)
    for name, href in link_map.items():
        if '>%s<' % name in card:
            card = re.sub(r'href="[^"]*"', 'href="%s"' % href, card, count=1)
            break
    return card

# 匹配 <a class="work-card" ...> 卡片
new_html = re.sub(r'<a class="work-card"[^>]*>[^<]*<div class="img-wrap"',
                  lambda m: replace_links(m),
                  html)

with open('zisha.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print('\nDone: %d detail pages created, zisha.html updated.' % len(works))
