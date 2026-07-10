/**
 * 龙兄知识库 · 全局 JavaScript v3
 * 纯原生，无框架依赖
 * 
 * [BUG-FIX:五-1] 代码分区：
 *   区域A - XSS防护与工具函数
 *   区域B - 主题切换（深浅色）
 *   区域C - 汉堡菜单（移动端导航）
 *   区域D - 搜索（首页+全站+本页高亮）
 *   区域E - 一键复制
 *   区域F - 面包屑
 *   区域G - 访客留言
 *   区域H - 滚动淡入动画
 */
(function(){
'use strict';

// ============================================================
// 区域A - XSS防护与工具函数
// [BUG-FIX:五-2] XSS防护加固
// ============================================================
function escapeHtml(t){
  if(!t)return'';
  var d=document.createElement('div');
  d.textContent=t;
  return d.innerHTML;
}
// [BUG-FIX:五-2] 搜索输入XSS过滤：移除HTML标签和特殊字符
function sanitizeInput(t){
  if(!t)return'';
  return t.replace(/<[^>]*>/g,'').replace(/[<>"'&]/g,function(c){
    return{'<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','&':'&amp;'}[c];
  });
}

// ============================================================
// 区域B - 主题切换（深浅色）
// [BUG-FIX:二-1] 放大切换按钮点击区域
// [BUG-FIX:二-2] 两套独立配色同步
// [BUG-FIX:二-3] localStorage永久保存
// [BUG-FIX:二-4] 消除闪白（head内联脚本+此处applyTheme）
// ============================================================
var THEME_KEY='theme';

function getAutoTheme(){
  // [优化:二-1] 优先用系统prefers-color-scheme，更准确
  if(window.matchMedia){
    try{
      if(window.matchMedia('(prefers-color-scheme: light)').matches)return'light';
      if(window.matchMedia('(prefers-color-scheme: dark)').matches)return'dark';
    }catch(e){}
  }
  // 回退：按时间判断
  var h=new Date().getHours();
  return(h>=6&&h<18)?'light':'dark';
}

function applyTheme(t){
  document.documentElement.setAttribute('data-theme',t);
  localStorage.setItem(THEME_KEY,t);
  updateThemeIcon(t);
}

function updateThemeIcon(t){
  var btn=document.getElementById('themeToggle');
  if(!btn)return;
  var sun=btn.querySelector('.icon-sun'),moon=btn.querySelector('.icon-moon');
  if(sun&&moon){
    // [BUG-FIX:二-2] 确保图标显隐正确：dark模式显示太阳（点击切到light），light模式显示月亮
    sun.style.display=t==='dark'?'inline':'none';
    moon.style.display=t==='dark'?'none':'inline';
  }
}

(function initTheme(){
  // [BUG-FIX:二-3] 从localStorage恢复，刷新不重置
  var saved=localStorage.getItem(THEME_KEY);
  var theme=(saved==='dark'||saved==='light')?saved:getAutoTheme();
  applyTheme(theme);
  // [BUG-FIX:二-1] icon-btn已有min-height:44px，此处确认绑定正确
  var btn=document.getElementById('themeToggle');
  if(btn)btn.addEventListener('click',function(){
    var cur=document.documentElement.getAttribute('data-theme')||'dark';
    applyTheme(cur==='dark'?'light':'dark');
  });
})();

// ============================================================
// 区域C - 汉堡菜单（移动端导航）
// [BUG-FIX:三-2] 放大触屏点击区域，展开/收起稳定
// ============================================================
(function(){
  var hb=document.querySelector('.hamburger');
  var mn=document.querySelector('.mobile-nav');
  if(!hb)return;
  if(!mn){
    mn=document.createElement('div');
    mn.className='mobile-nav';
    mn.id='mobileNav';
    var navLinks=document.querySelector('.nav-links');
    if(navLinks){
      navLinks.querySelectorAll('a').forEach(function(a){
        var clone=a.cloneNode(true);
        clone.addEventListener('click',function(){hb.classList.remove('active');mn.classList.remove('open');});
        mn.appendChild(clone);
      });
    }
    hb.parentElement.parentElement.appendChild(mn);
  }
  hb.addEventListener('click',function(e){
    e.stopPropagation();
    hb.classList.toggle('active');
    mn.classList.toggle('open');
  });
  mn.querySelectorAll('a').forEach(function(a){
    a.addEventListener('click',function(){hb.classList.remove('active');mn.classList.remove('open');});
  });
  document.addEventListener('click',function(e){
    if(!hb.contains(e.target)&&!mn.contains(e.target)){
      hb.classList.remove('active');mn.classList.remove('open');
    }
  });
})();

// ============================================================
// 区域D - 搜索已拆分至 js/search.js 独立加载 [六-1]
// ============================================================

// ============================================================
// 区域E - 一键复制
// [BUG-FIX:三-1] 修复点击无反应、复制文字缺失、手机点击区域过小
// [BUG-FIX:三-1] 复制成功显示简易提示
// ============================================================
function copyText(text,btn){
  function done(){
    // [BUG-FIX:三-1] 复制成功显示简易提示
    var orig=btn.textContent;
    btn.textContent='已复制 ✓';
    btn.classList.add('copied');
    setTimeout(function(){btn.textContent=orig;btn.classList.remove('copied');},2000);
  }
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(function(){fallbackCopy(text,done);});
  }else{
    fallbackCopy(text,done);
  }
}
function fallbackCopy(text,done){
  var ta=document.createElement('textarea');
  ta.value=text;
  ta.style.cssText='position:fixed;left:-9999px;top:-9999px;opacity:0';
  ta.setAttribute('readonly','');
  document.body.appendChild(ta);
  var range=document.createRange();range.selectNodeContents(ta);
  var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);
  try{document.execCommand('copy');done();}catch(x){}
  sel.removeAllRanges();document.body.removeChild(ta);
}

// [BUG-FIX:三-1] 事件委托处理复制按钮点击
document.addEventListener('click',function(e){
  var btn=e.target.closest('.copy-btn');if(!btn)return;
  var target=btn.getAttribute('data-copy-target');
  // [BUG-FIX:三-1] 修复复制文字缺失：优先用data-copy-text，其次用target元素内容
  var text='';
  if(btn.getAttribute('data-copy-text')){
    text=btn.getAttribute('data-copy-text');
  }else if(target){
    var el=document.querySelector(target);
    text=el?el.textContent||'':'';
  }else{
    // 找最近的代码块或提示框内容
    var parent=btn.closest('pre, .tip-box, .warning-box, .info-box');
    text=parent?parent.textContent||'':'';
  }
  if(!text)return;
  copyText(text,btn);
});

// 自动添加复制按钮
function autoCopyButtons(){
  document.querySelectorAll('pre').forEach(function(b){
    if(b.parentElement.classList.contains('code-block-wrapper'))return;
    var w=document.createElement('div');w.className='code-block-wrapper';w.style.position='relative';
    b.parentNode.insertBefore(w,b);w.appendChild(b);
    var btn=document.createElement('button');btn.className='copy-btn code-copy-btn';btn.textContent='📋 复制';
    btn.setAttribute('data-copy-text',b.textContent||'');
    // [BUG-FIX:三-1] 手机点击区域过小：确保min-height/min-width
    btn.style.cssText='position:absolute;top:8px;right:8px;z-index:10;min-height:44px;min-width:44px;';
    w.appendChild(btn);
  });
  document.querySelectorAll('.tip-box,.warning-box,.info-box').forEach(function(box){
    if(box.querySelector('.copy-btn'))return;
    var btn=document.createElement('button');btn.className='copy-btn box-copy-btn';btn.textContent='复制';
    btn.setAttribute('data-copy-text',box.textContent||'');
    // [BUG-FIX:三-1] 手机点击区域过小
    btn.style.cssText='position:absolute;bottom:8px;right:8px;z-index:10;font-size:0.75rem;padding:4px 10px;min-height:44px;min-width:44px;';
    box.style.position='relative';box.appendChild(btn);
  });
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',autoCopyButtons);else autoCopyButtons();

// ============================================================
// 区域F - 面包屑
// ============================================================
(function(){
  var c=document.getElementById('breadcrumb');if(!c)return;
  var path=window.location.pathname;
  var parts=path.replace(/\/$/,'').split('/').filter(Boolean);
  var titleMap={
    'agarwood':'沉香鉴别','bracelet':'文玩手串','herbs':'中药材与香料',
    'health-tea':'中药养生茶','sheyang':'射阳天气','xintan-weather':'新坍镇农田气象','tesla':'特斯拉动态新闻',
    'changelog':'更新日志','index':'首页',
    'diguniu':'地牯牛','dilong':'地龙','huashicao':'化石草',
    'huashifen':'滑石粉','jiangzhenxiang':'降真香','maoshikafei':'猫屎咖啡',
    'shuizhi':'水蛭','wulingzhi':'五灵脂','xiongdan':'熊胆',
    'model3':'Model 3','modely':'Model Y','modelyl':'Model Y L','models':'Model S','modelx':'Model X',
    'cybertruck':'赛博皮卡','semi':'Semi 电动重卡','roadster':'Roadster 超跑','cybercab':'Cybercab 无人驾驶出租车',
    'powerwall':'Powerwall 家庭储能','megapack':'Megapack 商用储能',
    'charging':'充电指南','accessories':'车载配件','maintenance':'保养维修',
    'fengyan':'凤眼菩提','longyan':'龙眼菩提','magu':'麻古菩提',
    'mengma':'猛犸','pinxiang':'品香','quanao':'拳脑','wuxing':'五行','xingyue':'星月菩提','zijinboyu':'紫金钵鱼'
  };
  var crumbs=[{label:'首页',url:'index.html'}];
  for(var i=0;i<parts.length;i++){
    var name=parts[i].replace(/\.html?$/i,'');
    if(name==='index'&&i===parts.length-1)continue;
    var url='';for(var j=0;j<=i;j++)url+=(j>0?'/':'')+parts[j];
    crumbs.push({label:titleMap[name]||name,url:url});
  }
  if(crumbs.length<=1){c.style.display='none';return;}
  var html='';
  crumbs.forEach(function(cr,i){
    var last=i===crumbs.length-1;
    html+=last?'<span class="current">'+escapeHtml(cr.label)+'</span>'
      :'<a href="'+escapeHtml(cr.url)+'">'+escapeHtml(cr.label)+'</a><span class="sep">›</span>';
  });
  c.innerHTML=html;c.className='breadcrumb';
})();

// ============================================================
// 区域H - 滚动淡入动画
// ============================================================
(function(){
  var items=document.querySelectorAll('.card,.tile,.method-tile,.step-tile,.phase-tile,.log-item,.timeline-item');
  if(!items.length)return;
  if(!('IntersectionObserver' in window)){items.forEach(function(el){el.classList.add('visible');});return;}
  var obs=new IntersectionObserver(function(entries){
    entries.forEach(function(entry){if(entry.isIntersecting){entry.target.classList.add('visible');obs.unobserve(entry.target);}});
  },{threshold:0.1});
  items.forEach(function(el){obs.observe(el);});
})();

// ============================================================
// 区域I - 活起来功能
// ============================================================

// 2. 页脚最后更新时间
(function(){
  var el=document.getElementById('lastModified');
  if(!el)return;
  var lm=document.lastModified;
  if(lm&&lm!=='01/01/0000'){
    try{
      var d=new Date(lm);
      var y=d.getFullYear();
      var m=('0'+(d.getMonth()+1)).slice(-2);
      var day=('0'+d.getDate()).slice(-2);
      var h=('0'+d.getHours()).slice(-2);
      var min=('0'+d.getMinutes()).slice(-2);
      el.textContent=y+'-'+m+'-'+day+' '+h+':'+min;
    }catch(e){el.textContent=lm;}
  }else{
    el.textContent='2026-06-24';
  }
})();



// 5. 今日龙兄在干嘛（内嵌到龙兄公示牌）
(function(){
  var inline = document.getElementById('todayStatusInline');
  var textEl = document.getElementById('todayStatusText');
  var dateEl = document.getElementById('todayStatusDate');
  if(!inline || !textEl) return;
  fetch('status.json?v='+Date.now())
    .then(function(r){if(!r.ok)throw new Error('Not found');return r.json();})
    .then(function(data){
      if(data && data.status && data.status.trim() !== ''){
        textEl.textContent = data.status;
        if(data.date) dateEl.textContent = '（' + data.date + '）';
        inline.style.display = 'block';
      } else {
        inline.style.display = 'none';
      }
    })
    .catch(function(){
      if(inline) inline.style.display = 'none';
    });
})();


// 4. 实时时钟（在天气页面自动初始化）
window.initClock=function(){
  var el=document.getElementById('liveClock');
  if(!el || el.dataset.init==='1') return;
  el.dataset.init='1';
  var dateEl=document.getElementById('liveDate');
  function tick(){
    var d=new Date();
    var h=('0'+d.getHours()).slice(-2);
    var m=('0'+d.getMinutes()).slice(-2);
    var s=('0'+d.getSeconds()).slice(-2);
    if(el)el.textContent=h+':'+m+':'+s;
    if(dateEl){
      var opts={year:'numeric',month:'long',day:'numeric',weekday:'long'};
      dateEl.textContent=d.toLocaleDateString('zh-CN',opts);
    }
  }
  tick();
  setInterval(tick,1000);
};

// 自动初始化天气页面时钟（无需页面再手动调用）
if(document.readyState==='loading'){
  document.addEventListener('DOMContentLoaded', window.initClock);
} else {
  window.initClock();
}

})();

// ── 全局导航栏时钟（每个页面都跑） ──
(function(){
  var el = document.getElementById('navClock');
  if(!el) return;
  function tick(){
    var d = new Date();
    var h = ('0'+d.getHours()).slice(-2);
    var m = ('0'+d.getMinutes()).slice(-2);
    var s = ('0'+d.getSeconds()).slice(-2);
    if(window.innerWidth<=768){
      el.textContent = h+':'+m;
    } else {
      el.textContent = h+':'+m+':'+s;
    }
  }
  tick();
  setInterval(tick, 1000);
})();

// ── 导航栏紧凑天气（全站共享，首页内联版优先） ──
(function(){
  var el = document.getElementById('navWeather');
  if(!el || el.dataset.init==='1') return; // 首页内联版已处理则跳过
  var WX={0:'☀️',1:'🌤️',2:'⛅',3:'☁️',45:'🌫️',48:'🌫️',51:'🌧️',53:'🌧️',55:'🌧️',61:'🌧️',63:'🌧️',65:'🌧️',71:'🌨️',73:'🌨️',75:'🌨️',77:'🌨️',80:'🌧️',81:'🌧️',82:'🌧️',85:'🌨️',86:'🌨️',95:'⛈️',96:'⛈️',99:'⛈️'};
  var URL='https://api.open-meteo.com/v1/forecast?latitude=33.77&longitude=120.52&current=temperature_2m,weather_code&timezone=Asia/Shanghai&forecast_days=1';
  function apply(t,c){ el.textContent=(WX[String(c)]||'🌡️')+' '+Math.round(t)+'°'; }
  fetch(URL).then(function(r){return r.json();}).then(function(d){
    if(d&&d.current) apply(d.current.temperature_2m,d.current.weather_code);
  }).catch(function(){
    el.textContent='🌤️--°';
  });
})();

// ============================================================
// 区域F - 导航高亮（当前页面）
// ============================================================
(function(){
  var path = window.location.pathname;
  var page = path.split('/').pop() || 'index.html';
  var links = document.querySelectorAll('.nav-links a, .mobile-nav a');
  links.forEach(function(a){
    var href = a.getAttribute('href') || '';
    if(!href || href.startsWith('#') || href.startsWith('http') || href.startsWith('//')) return;
    var hrefFile = href.split('/').pop();
    if(hrefFile === page){
      a.classList.add('active');
    }
    if(page === 'index.html'){
      if(hrefFile === 'index.html' || href === '' || href === './' || href === '/'){
        a.classList.add('active');
      }
    }
  });
})();

// ============================================================
// 区域G - 回到顶部按钮
// ============================================================
(function(){
  // 动态创建按钮
  var btn = document.createElement('button');
  btn.className = 'back-to-top';
  btn.setAttribute('aria-label', '回到顶部');
  btn.setAttribute('title', '回到顶部');
  btn.innerHTML = '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l-6-6-6 6"/></svg>';
  document.body.appendChild(btn);

  // 滚动监听
  var threshold = 500;
  var ticking = false;
  function check() {
    var y = window.scrollY || window.pageYOffset;
    if (y > threshold) {
      btn.classList.add('visible');
    } else {
      btn.classList.remove('visible');
    }
    ticking = false;
  }
  window.addEventListener('scroll', function() {
    if (!ticking) {
      requestAnimationFrame(check);
      ticking = true;
    }
  }, { passive: true });

  // 点击回到顶部
  btn.addEventListener('click', function() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  check();
})();

// ============================================================
// 区域H - 导航栏"更多"下拉菜单（点击切换）
// ============================================================
(function(){
  var btn = document.querySelector('.nav-more-btn');
  var wrap = document.querySelector('.nav-more-wrap');
  if (!btn || !wrap) return;

  // 点击"更多"按钮切换
  btn.addEventListener('click', function(e){
    e.preventDefault();
    e.stopPropagation();
    wrap.classList.toggle('open');
  });

  // 点击页面其他地方关闭
  document.addEventListener('click', function(e){
    if (wrap.classList.contains('open') && !wrap.contains(e.target)){
      wrap.classList.remove('open');
    }
  });

  // ESC关闭
  document.addEventListener('keydown', function(e){
    if (e.key === 'Escape' && wrap.classList.contains('open')){
      wrap.classList.remove('open');
    }
  });
})();

// ============================================================
// 区域I - 不蒜子访客统计 → 更新首页 magVisitorCount
// ============================================================
(function(){
  function updateVisitorCount(){
    var uvEl = document.getElementById('busuanzi_value_site_uv');
    var magVisitor = document.getElementById('magVisitorCount');
    if (!magVisitor) return; // 不在首页则无需处理

    // 不蒜子已加载数据（非空、非默认 -、非0）
    if (uvEl && uvEl.textContent && uvEl.textContent !== '-' && uvEl.textContent !== '0') {
      var uv = parseInt(uvEl.textContent.replace(/,/g, ''));
      if (!isNaN(uv) && uv > 0) {
        // 数字滚动动画
        var duration = 1200;
        var startTime = performance.now();
        function tick(now){
          var progress = Math.min((now - startTime) / duration, 1);
          magVisitor.textContent = Math.floor(uv * progress);
          if (progress < 1) requestAnimationFrame(tick);
          else magVisitor.textContent = uv;
        }
        requestAnimationFrame(tick);
        return;
      }
    }

    // 不蒜子尚未加载，重试（最多60次 × 500ms = 30秒）
    updateVisitorCount._retries = (updateVisitorCount._retries || 0) + 1;
    if (updateVisitorCount._retries < 60) {
      setTimeout(updateVisitorCount, 500);
    }
  }

  // DOM 就绪后启动（兼容已 loaded 和 loading 两种状态）
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', updateVisitorCount);
  } else {
    updateVisitorCount();
  }
})();

// ============================================================
// 区域J - 自动章节快速导航（解决长页面下拉疲劳）
// 自动扫描页面 h2 标题，生成粘性侧边导航（电脑端）
// + 底部浮动导航（手机端），带 scroll spy 高亮
// 已有自定义导航的页面（guanghui/zisha）自动跳过
// ============================================================
(function(){
  function initSectionNav(){
    // 跳过已有自定义导航的页面
    if(document.querySelector('.gh-sidenav') || document.querySelector('.gh-page')) return;
    // zisha.html 已有 .section-nav，但它是页面内嵌的水平导航，不是侧边浮动
    // 仍然跳过避免重复
    if(document.querySelector('.section-nav') && document.querySelector('.gh-sidenav') === null){
      // zisha 的 section-nav 是页面内嵌的，我们给它增强但不重复创建
      // 实际上 zisha 的 section-nav 已经是页内导航了，跳过
      var existingNav = document.querySelector('.section-nav');
      if(existingNav && existingNav.children.length >= 3) return;
    }

    // 扫描 h2 标题
    var headings = [];
    var allH2 = document.querySelectorAll('h2');
    allH2.forEach(function(h){
      // 跳过隐藏的、在 script/template 中的
      if(h.closest('script') || h.closest('template')) return;
      if(h.offsetParent === null && getComputedStyle(h).display === 'none') return;
      var text = (h.textContent || '').trim();
      if(!text || text.length < 2) return;
      headings.push(h);
    });

    // 少于3个 h2 不生成导航
    if(headings.length < 3) return;

    // 给没有 id 的 h2 生成 id
    headings.forEach(function(h, i){
      if(!h.id){
        h.id = 'sec-nav-' + i;
      }
      h.setAttribute('data-secnav', 'true');
    });

    // 准备导航项（最多取8个，避免太长）
    var maxItems = headings.length > 8 ? 8 : headings.length;
    var navItems = [];
    for(var i = 0; i < maxItems; i++){
      var h = headings[i];
      var text = (h.textContent || '').trim();
      // 清理 emoji 前缀，取核心文字（截断到20字）
      var cleanText = text.replace(/^[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]+\s*/u, '');
      if(cleanText.length > 16) cleanText = cleanText.substring(0, 16) + '…';
      if(!cleanText) cleanText = text.substring(0, 16);
      navItems.push({ id: h.id, text: cleanText, fullText: text });
    }

    // 注入 CSS（只注入一次）
    if(!document.getElementById('secnav-styles')){
      var style = document.createElement('style');
      style.id = 'secnav-styles';
      style.textContent = [
        '/* 自动章节导航 */',
        '.secnav-side{',
          'position:fixed;left:20px;top:50%;transform:translateY(-50%);',
          'z-index:90;max-height:70vh;overflow-y:auto;',
          'display:flex;flex-direction:column;gap:2px;',
          'padding:10px 8px;border-radius:12px;',
          'background:var(--card);border:1px solid var(--border);',
          'box-shadow:var(--shadow-md);',
          'opacity:0;visibility:hidden;',
          'transition:opacity .3s,visibility .3s;',
          'min-width:130px;max-width:180px;',
        '}',
        '.secnav-side.visible{opacity:1;visibility:visible;}',
        '.secnav-side a{',
          'display:block;padding:6px 12px;border-radius:6px;',
          'font-size:0.78rem;color:var(--text-secondary);',
          'text-decoration:none;cursor:pointer;',
          'transition:all .2s;white-space:nowrap;',
          'overflow:hidden;text-overflow:ellipsis;',
          'border-left:2px solid transparent;',
        '}',
        '.secnav-side a:hover{color:var(--text);background:var(--card-hover);}',
        '.secnav-side a.active{',
          'color:var(--gold);border-left-color:var(--gold);',
          'background:rgba(201,168,76,0.08);font-weight:600;',
        '}',
        '.secnav-side .secnav-title{',
          'font-size:0.7rem;color:var(--text-muted);',
          'padding:4px 12px 8px;border-bottom:1px solid var(--border);',
          'margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px;',
        '}',
        '/* 手机端底部导航 */',
        '.secnav-bottom{',
          'position:fixed;bottom:0;left:0;right:0;z-index:91;',
          'display:none;align-items:center;gap:4px;',
          'padding:8px 12px;overflow-x:auto;',
          'background:var(--nav-bg);backdrop-filter:blur(12px);',
          'border-top:1px solid var(--border);',
          'scrollbar-width:none;-ms-overflow-style:none;',
        '}',
        '.secnav-bottom::-webkit-scrollbar{display:none;}',
        '.secnav-bottom a{',
          'flex-shrink:0;padding:6px 14px;border-radius:20px;',
          'font-size:0.75rem;color:var(--text-secondary);',
          'text-decoration:none;white-space:nowrap;',
          'background:var(--card);border:1px solid var(--border);',
          'transition:all .2s;',
        '}',
        '.secnav-bottom a:hover{color:var(--text);}',
        '.secnav-bottom a.active{',
          'color:var(--gold);border-color:var(--gold);',
          'background:rgba(201,168,76,0.12);',
        '}',
        '/* 响应式切换 */',
        '@media (max-width:900px){',
          '.secnav-side{display:none;}',
          '.secnav-bottom.visible{display:flex;}',
          'body.has-secnav{padding-bottom:50px;}',
        '}',
        '@media (min-width:901px){',
          '.secnav-bottom{display:none;}',
        '}',
        '/* 滚动条美化 */',
        '.secnav-side::-webkit-scrollbar{width:4px;}',
        '.secnav-side::-webkit-scrollbar-track{background:transparent;}',
        '.secnav-side::-webkit-scrollbar-thumb{background:var(--border-light);border-radius:2px;}'
      ].join('\n');
      document.head.appendChild(style);
    }

    // 创建电脑端侧边导航
    var sideNav = document.createElement('nav');
    sideNav.className = 'secnav-side';
    sideNav.setAttribute('aria-label', '页面章节导航');
    var sideHtml = '<div class="secnav-title">📑 快速跳转</div>';
    navItems.forEach(function(item){
      sideHtml += '<a href="#' + item.id + '" data-target="' + item.id + '" title="' + 
        item.fullText.replace(/"/g, '&quot;') + '">' + item.text + '</a>';
    });
    sideNav.innerHTML = sideHtml;
    document.body.appendChild(sideNav);

    // 创建手机端底部导航
    var bottomNav = document.createElement('nav');
    bottomNav.className = 'secnav-bottom';
    bottomNav.setAttribute('aria-label', '页面章节导航');
    var bottomHtml = '';
    navItems.forEach(function(item){
      bottomHtml += '<a href="#' + item.id + '" data-target="' + item.id + '">' + item.text + '</a>';
    });
    bottomNav.innerHTML = bottomHtml;
    document.body.appendChild(bottomNav);
    document.body.classList.add('has-secnav');

    // 平滑滚动
    function scrollToSection(id){
      var target = document.getElementById(id);
      if(!target) return;
      var navHeight = 60; // 导航栏高度
      var rect = target.getBoundingClientRect();
      var top = window.scrollY + rect.top - navHeight - 10;
      window.scrollTo({ top: top, behavior: 'smooth' });
    }

    // 点击事件
    [sideNav, bottomNav].forEach(function(nav){
      nav.querySelectorAll('a').forEach(function(a){
        a.addEventListener('click', function(e){
          e.preventDefault();
          var id = a.getAttribute('data-target');
          scrollToSection(id);
        });
      });
    });

    // 滚动显示/隐藏 + Scroll Spy
    var scrollThreshold = 300;
    var ticking = false;
    var currentActive = null;

    function update(){
      var scrollY = window.scrollY || window.pageYOffset;

      // 显示/隐藏
      if(scrollY > scrollThreshold){
        sideNav.classList.add('visible');
        bottomNav.classList.add('visible');
      } else {
        sideNav.classList.remove('visible');
        bottomNav.classList.remove('visible');
      }

      // Scroll Spy: 找到当前可见的标题
      var activeId = null;
      for(var i = headings.length - 1; i >= 0; i--){
        var rect = headings[i].getBoundingClientRect();
        if(rect.top <= 120 && rect.bottom > 60){
          activeId = headings[i].id;
          break;
        }
      }
      // 如果没找到（可能在页面最顶部），选第一个
      if(!activeId && scrollY < 200 && headings.length > 0){
        activeId = headings[0].id;
      }

      if(activeId !== currentActive){
        currentActive = activeId;
        [sideNav, bottomNav].forEach(function(nav){
          nav.querySelectorAll('a').forEach(function(a){
            if(a.getAttribute('data-target') === activeId){
              a.classList.add('active');
            } else {
              a.classList.remove('active');
            }
          });
        });

        // 手机端：自动滚动到活跃项
        if(activeId && window.innerWidth <= 900){
          var activeLink = bottomNav.querySelector('a.active');
          if(activeLink){
            var navRect = bottomNav.getBoundingClientRect();
            var linkRect = activeLink.getBoundingClientRect();
            if(linkRect.left < navRect.left || linkRect.right > navRect.right){
              activeLink.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
            }
          }
        }
      }

      ticking = false;
    }

    window.addEventListener('scroll', function(){
      if(!ticking){
        requestAnimationFrame(update);
        ticking = true;
      }
    }, { passive: true });

    update();
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initSectionNav);
  } else {
    initSectionNav();
  }
})();
