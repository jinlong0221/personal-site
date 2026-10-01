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
// 区域Z - 移动端表格横向滚动包裹 [MOBILE-FIX]
// 宽表格(.m-table min-width:640px / .scoreline-table 400px / .changelog-table 600px)
// 在窄屏会横向溢出被 overflow-x:hidden 裁切。把未包裹的表格装入 .table-wrapper
// (已有 overflow-x:auto + 首列 sticky + 滚动提示)，统一修复所有内容页表格。
// ============================================================
(function(){
  function wrapTables(){
    var tables = document.querySelectorAll(
      '.content-body table, table.m-table, table.scoreline-table, .changelog-table table'
    );
    Array.prototype.forEach.call(tables, function(t){
      if(t.closest('.table-wrapper')) return;
      var wrap = document.createElement('div');
      wrap.className = 'table-wrapper';
      t.parentNode.insertBefore(wrap, t);
      wrap.appendChild(t);
    });
  }
  if(document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wrapTables);
  else wrapTables();
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
  var c=document.getElementById('breadcrumb');if(!c||c.innerHTML.trim())return;
  var path=window.location.pathname;
  var parts=path.replace(/\/$/,'').split('/').filter(Boolean);
  var titleMap={
    'bracelet':'文玩手串',
    'health-tea':'养生茶','sheyang':'射阳天气','xintan-weather':'新坍镇农田气象','tesla':'特斯拉动态新闻',
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
  fetch('status.json?v='+Math.floor(Date.now()/600000))
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

// ── 导航栏紧凑天气（全站共享，SVG 图标 + 实时温度）──
(function(){
  var el = document.getElementById('navWeather');
  if(!el) return;
  var URL='https://api.open-meteo.com/v1/forecast?latitude=33.77&longitude=120.52&current=temperature_2m,weather_code&timezone=Asia/Shanghai&forecast_days=1';
  var ICONS={
    sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2.5M12 19.5v2.5M4.2 4.2l1.8 1.8M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8l1.8-1.8M18 6l1.8-1.8"/>',
    'cloud-sun':'<circle cx="8.5" cy="8.5" r="3"/><path d="M8.5 2.5v2M3.3 8.5h2M4.6 4.6l1.4 1.4"/><path d="M11 18a3.2 3.2 0 010-6.4 4.2 4.2 0 018.1-1.2A3.2 3.2 0 0118.5 18H11z"/>',
    cloud:'<path d="M7 18a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 18H7z"/>',
    fog:'<path d="M7 17a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 17H7z"/><path d="M7 20h11M8.5 22.5h8"/>',
    rain:'<path d="M7 16a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 16H7z"/><path d="M8 19l-1 3M12 19l-1 3M16 19l-1 3"/>',
    snow:'<path d="M7 16a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 16H7z"/><path d="M8 19.5v3M12 19.5v3M16 19.5v3"/>',
    thunder:'<path d="M7 16a4 4 0 010-8 5 5 0 019.6-1.5A4 4 0 0118 16H7z"/><path d="M11 18l-2.5 4h3l-2.5 4"/>'
  };
  function svg(key){ return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(ICONS[key]||ICONS.cloud)+'</svg>'; }
  function keyFor(c){ c=+c;
    if(c===0) return 'sun';
    if(c===1||c===2) return 'cloud-sun';
    if(c===3) return 'cloud';
    if(c===45||c===48) return 'fog';
    if(c>=51&&c<=67) return 'rain';
    if(c>=71&&c<=77) return 'snow';
    if(c>=80&&c<=86) return 'rain';
    if(c>=95) return 'thunder';
    return 'cloud';
  }
  function apply(t,c){ el.innerHTML = svg(keyFor(c)) + '<span style="margin-left:3px">'+Math.round(t)+'°</span>'; }
  fetch(URL).then(function(r){return r.json();}).then(function(d){
    if(d&&d.current) apply(d.current.temperature_2m,d.current.weather_code);
    else el.innerHTML = svg('cloud')+'<span style="margin-left:3px">--°</span>';
  }).catch(function(){
    el.innerHTML = svg('cloud')+'<span style="margin-left:3px">--°</span>';
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
  var threshold = 900;
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
// 区域H2 - 导航自适应收纳：空间不够时把靠后的顶级导航项收进"更多"下拉
// 根治：769~1250px 区间导航总宽超出容器、站名曾被裁切的问题。
// 收进下拉的是真实 <li>（原样搬移），窗口拉宽自动放回原位，任何宽度不丢链接。
// 时序要点：时钟 JS 异步填数字、毛笔字体会晚到——这些都让子元素变宽，
// 所以用 ResizeObserver 盯住导航全部子元素，宽度一变就重测，不靠单一时机。
// ============================================================
(function(){
  var inner = document.querySelector('.navbar-inner');
  var ul = document.querySelector('.nav-links');
  var moreLi = document.querySelector('.nav-more-wrap');
  var dd = document.querySelector('.nav-more-dropdown');
  if(!inner || !ul || !moreLi || !dd) return;

  var moved = []; // 已收进下拉的 li；moved[0] 是最后收进去的（还原时最先放回）
  var ticking = false;

  function fits(){
    return inner.scrollWidth <= inner.clientWidth + 1;
  }
  function relayout(){
    ticking = false;
    // 收：溢出则从"更多"前一项开始逐个收进下拉
    // （下拉 absolute 不占布局宽，收纳严格减宽，单调收敛）
    var guard = 0;
    while(!fits() && guard++ < 15){
      var lis = ul.children;
      if(lis.length <= 1) break;          // 只剩"更多"就不再收
      var li = lis[lis.length - 2];
      ul.removeChild(li);
      dd.insertBefore(li, dd.firstChild); // 收进下拉最上方
      moved.unshift(li);
    }
    // 放：有余量时尝试还原一项。带 20px 安全余量防抖动：
    // 余量不足以容纳"该项宽 + 12px 项间距 + 20px 缓冲"就不放，
    // 避免放回→溢出→收走→放回的死循环。
    if(fits() && moved.length){
      var spare = inner.clientWidth - inner.scrollWidth; // 当前富余宽度
      var cand = moved[0];
      var w = cand.getBoundingClientRect().width; // 下拉里 block 展示宽≈顶栏宽
      if(spare >= w + 32){
        dd.removeChild(cand);
        ul.insertBefore(cand, moreLi);
        moved.shift();
      }
    }
  }
  function schedule(){
    if(!ticking){ ticking = true; requestAnimationFrame(relayout); }
  }
  window.addEventListener('resize', schedule, { passive: true });
  window.addEventListener('load', schedule);
  if(document.fonts && document.fonts.ready){ document.fonts.ready.then(schedule); }
  if(window.ResizeObserver){
    var ro = new ResizeObserver(schedule);
    Array.prototype.forEach.call(inner.children, function(el){ ro.observe(el); });
  }
  relayout();
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
    // 页面级显式禁用自动章节导航（长页面自身已有导航/筛选条时避免重复浮层）
    if(document.body.getAttribute('data-no-secnav') === 'true') return;
    // 跳过已有自定义侧边导航的页面
    if(document.querySelector('.gh-sidenav') || document.querySelector('.gh-page')) return;
    // zisha.html 的 .section-nav 为页内水平导航，避免重复生成
    if(document.querySelector('.section-nav') && !document.querySelector('.gh-sidenav')){
      var exNav = document.querySelector('.section-nav');
      if(exNav && exNav.children.length >= 3) return;
    }

    // 扫描 h2/h3 标题，构建大纲树
    var tree = [];
    var all = [];
    var current = null;
    var hs = document.querySelectorAll('h2, h3');
    hs.forEach(function(h){
      if(h.closest('script') || h.closest('template')) return;
      if(h.offsetParent === null && getComputedStyle(h).display === 'none') return;
      var level = h.tagName === 'H2' ? 2 : 3;
      var text = (h.textContent || '').trim();
      if(!text || text.length < 2) return;
      if(level === 2){
        current = { el:h, level:2, text:text, children:[] };
        tree.push(current);
        all.push(current);
      } else if(current){
        var sub = { el:h, level:3, text:text, parent:current };
        current.children.push(sub);
        all.push(sub);
      }
    });

    // 触发条件：h2 >= 3，或（有 h2 且 总标题数 >= 4）
    if(tree.length < 3 && !(tree.length >= 1 && all.length >= 4)) return;

    // 给没有 id 的标题生成 id
    all.forEach(function(node, i){
      if(!node.el.id) node.el.id = 'toc-' + i;
      node.el.setAttribute('data-toc', 'true');
    });

    // 清理 emoji / 符号前缀并截断
    function clean(t, max){
      var c = t.replace(/^[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}\u{2705}\u{274C}\u{2714}\u{2716}]+\s*/u, '');
      c = c.replace(/^[✔✅❌⭕▶▸•·\-—]+/, '').trim();
      if(c.length > max) c = c.substring(0, max) + '…';
      return c || t.substring(0, max);
    }

    // 注入样式（仅一次）
    if(!document.getElementById('secnav-styles')){
      var style = document.createElement('style');
      style.id = 'secnav-styles';
      style.textContent = [
        '/* 自动章节导航 v2 */',
        '.reading-progress{position:fixed;top:0;left:0;height:3px;width:0;z-index:201;',
        'background:linear-gradient(90deg,var(--gold),var(--gold-light));',
        'box-shadow:0 0 8px rgba(201,168,76,.6);transition:width .12s linear;}',
        '.secnav-side{position:fixed;right:20px;top:50%;transform:translateY(-50%);',
        'z-index:90;max-height:72vh;overflow-y:auto;display:flex;flex-direction:column;gap:2px;',
        'padding:14px 10px 14px 12px;border-radius:14px;background:var(--card);',
        'border:1px solid var(--border);box-shadow:var(--shadow-md);',
        'opacity:0;visibility:hidden;transition:opacity .3s,visibility .3s;min-width:160px;max-width:220px;}',
        '.secnav-side.visible{opacity:1;visibility:visible;}',
        '.secnav-side .secnav-title{font-size:0.72rem;color:var(--text-muted);',
        'padding:2px 12px 10px;margin-bottom:6px;border-bottom:1px solid var(--border);',
        'letter-spacing:1px;font-weight:700;}',
        '.secnav-side a{display:block;padding:6px 12px;border-radius:7px;font-size:0.82rem;',
        'color:var(--text-secondary);text-decoration:none;cursor:pointer;transition:all .2s;',
        'line-height:1.45;border-left:2px solid transparent;}',
        '.secnav-side a:hover{color:var(--text);background:var(--card-hover);}',
        '.secnav-side a.toc-h3{padding-left:26px;font-size:0.78rem;color:var(--text-muted);}',
        '.secnav-side a.active{color:var(--gold);border-left-color:var(--gold);',
        'background:rgba(201,168,76,0.10);font-weight:600;}',
        '.secnav-side a.toc-h3.active{color:var(--gold-light);}',
        '.secnav-bottom{position:fixed;bottom:0;left:0;right:0;z-index:91;display:none;',
        'align-items:center;gap:4px;padding:8px 12px;overflow-x:auto;background:var(--nav-bg);',
        'backdrop-filter:blur(12px);border-top:1px solid var(--border);',
        'scrollbar-width:none;-ms-overflow-style:none;}',
        '.secnav-bottom::-webkit-scrollbar{display:none;}',
        '.secnav-bottom a{flex-shrink:0;padding:6px 14px;border-radius:20px;font-size:0.75rem;',
        'color:var(--text-secondary);text-decoration:none;white-space:nowrap;',
        'background:var(--card);border:1px solid var(--border);transition:all .2s;}',
        '.secnav-bottom a:hover{color:var(--text);}',
        '.secnav-bottom a.active{color:var(--gold);border-color:var(--gold);',
        'background:rgba(201,168,76,0.12);}',
        '.secnav-bottom .secnav-toggle{flex-shrink:0;width:30px;height:30px;',
        'display:flex;align-items:center;justify-content:center;border-radius:50%;',
        'background:var(--card);border:1px solid var(--border);color:var(--text-secondary);',
        'cursor:pointer;margin-left:4px;transition:transform .2s,background .2s,color .2s;}',
        '.secnav-bottom .secnav-toggle:hover{background:var(--card-hover);color:var(--text);}',
        '.secnav-bottom.is-expanded .secnav-toggle{transform:rotate(180deg);}',
        '.secnav-bottom .secnav-toggle svg{width:16px;height:16px;}',
        '.secnav-bottom .secnav-current{flex-shrink:0;padding:6px 14px;border-radius:20px;',
        'font-size:0.75rem;color:var(--gold);white-space:nowrap;',
        'background:rgba(201,168,76,0.12);border:1px solid var(--gold);',
        'display:none;cursor:pointer;}',
        '.toc-top{position:fixed;right:22px;bottom:24px;z-index:95;width:44px;height:44px;',
        'display:flex;align-items:center;justify-content:center;border-radius:50%;',
        'background:var(--card);border:1px solid var(--gold);color:var(--gold);',
        'box-shadow:var(--shadow-md);cursor:pointer;opacity:0;visibility:hidden;',
        'transition:opacity .3s,visibility .3s,background .2s,transform .2s;}',
        '.toc-top.visible{opacity:1;visibility:visible;}',
        '.toc-top:hover{background:var(--gold);color:#1a1a1a;transform:translateY(-2px);}',
        '.toc-top svg{width:20px;height:20px;}',
        /* 目录浮层宽约 214px（右缘 20px + 本体约 194px），正文容器 1200px 居中：
           视口 < 1200/2 + 214 ≈ 1628px 时右侧余量不足，侧目录会压住正文，
           此时隐藏侧目录、改用底部目录条（与窄屏同一套交互） */
        '@media (max-width:1628px){',
        '.secnav-side{display:none;}.secnav-bottom.visible{display:flex;}',
        'body.has-secnav{padding-bottom:52px;}.toc-top{bottom:64px;}}',
        /* 移动端默认折叠底部目录条，只显示当前章节 + 展开按钮，避免占屏 */
        '@media (max-width:768px){',
        '.secnav-bottom:not(.is-expanded){padding:8px 14px;}',
        '.secnav-bottom:not(.is-expanded) a{display:none;}',
        '.secnav-bottom:not(.is-expanded) .secnav-current{display:inline-flex;}',
        '.secnav-bottom.is-expanded .secnav-current{display:none;}',
        '.secnav-bottom:not(.is-expanded) .secnav-toggle{margin-left:auto;}}',
        '@media (min-width:769px){.secnav-bottom .secnav-current{display:none;}.secnav-bottom .secnav-toggle{display:none;}}',
        '@media (min-width:1629px){.secnav-bottom{display:none;}}',
        '.secnav-side::-webkit-scrollbar{width:4px;}',
        '.secnav-side::-webkit-scrollbar-track{background:transparent;}',
        '.secnav-side::-webkit-scrollbar-thumb{background:var(--border-light);border-radius:2px;}'
      ].join('\n');
      document.head.appendChild(style);
    }

    // 生成右侧目录（嵌套 h3）
    var sideNav = document.createElement('nav');
    sideNav.className = 'secnav-side';
    sideNav.setAttribute('aria-label', '页面目录');
    var sideHtml = '<div class="secnav-title">目录</div>';
    var sideCount = 0;
    var SIDE_MAX = 16;
    tree.forEach(function(node){
      if(sideCount >= SIDE_MAX) return;
      sideHtml += '<a href="#' + node.el.id + '" class="toc-h2" data-target="' + node.el.id + '" title="' +
        node.text.replace(/"/g,'&quot;') + '">' + clean(node.text, 18) + '</a>';
      sideCount++;
      node.children.forEach(function(sub){
        if(sideCount >= SIDE_MAX) return;
        sideHtml += '<a href="#' + sub.el.id + '" class="toc-h3" data-target="' + sub.el.id + '" title="' +
          sub.text.replace(/"/g,'&quot;') + '">' + clean(sub.text, 16) + '</a>';
        sideCount++;
      });
    });
    sideNav.innerHTML = sideHtml;
    document.body.appendChild(sideNav);

    // 生成底部导航（扁平）
    var bottomNav = document.createElement('nav');
    bottomNav.className = 'secnav-bottom';
    bottomNav.setAttribute('aria-label', '页面目录');
    var chevronSvg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
    var bottomHtml = '<button class="secnav-current" aria-label="展开目录"></button>';
    all.forEach(function(node){
      bottomHtml += '<a href="#' + node.el.id + '" data-target="' + node.el.id + '">' +
        clean(node.text, 14) + '</a>';
    });
    bottomHtml += '<button class="secnav-toggle" aria-label="展开/收起目录" aria-expanded="false">' + chevronSvg + '</button>';
    bottomNav.innerHTML = bottomHtml;
    document.body.appendChild(bottomNav);
    document.body.classList.add('has-secnav');
    // 移动端默认折叠，桌面/平板默认展开
    if(window.innerWidth <= 768){
      bottomNav.classList.remove('is-expanded');
    } else {
      bottomNav.classList.add('is-expanded');
    }

    // 阅读进度条
    var progress = document.createElement('div');
    progress.className = 'reading-progress';
    document.body.appendChild(progress);

    // 平滑滚动
    function scrollToId(id){
      var target = document.getElementById(id);
      if(!target) return;
      var navH = 60;
      var rect = target.getBoundingClientRect();
      var top = window.scrollY + rect.top - navH - 12;
      window.scrollTo({ top: top, behavior: 'smooth' });
    }
    var currentBtn = bottomNav.querySelector('.secnav-current');
    var toggleBtn = bottomNav.querySelector('.secnav-toggle');
    function setBottomExpanded(expanded){
      bottomNav.classList.toggle('is-expanded', expanded);
      if(toggleBtn) toggleBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
      if(currentBtn) currentBtn.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    }
    if(toggleBtn){
      toggleBtn.addEventListener('click', function(e){
        e.stopPropagation();
        setBottomExpanded(!bottomNav.classList.contains('is-expanded'));
      });
    }
    if(currentBtn){
      currentBtn.addEventListener('click', function(e){
        e.stopPropagation();
        setBottomExpanded(true);
      });
    }
    [sideNav, bottomNav].forEach(function(nav){
      nav.querySelectorAll('a').forEach(function(a){
        a.addEventListener('click', function(e){
          e.preventDefault();
          scrollToId(a.getAttribute('data-target'));
          // 移动端点击目录项后自动收起底部条
          if(nav === bottomNav && window.innerWidth <= 768){
            setBottomExpanded(false);
          }
        });
      });
    });
    // 点击页面其它区域收起底部目录条
    document.addEventListener('click', function(e){
      if(window.innerWidth > 768) return;
      if(!bottomNav.classList.contains('is-expanded')) return;
      if(bottomNav.contains(e.target)) return;
      setBottomExpanded(false);
    });

    // 滚动处理：显示/隐藏 + scroll spy + 进度条
    var showThreshold = 300;
    var ticking = false;
    var currentActive = null;

    function update(){
      var scrollY = window.scrollY || window.pageYOffset;
      var docH = document.documentElement.scrollHeight - window.innerHeight;
      progress.style.width = (docH > 0 ? (scrollY / docH * 100) : 0) + '%';
      if(scrollY > showThreshold){
        sideNav.classList.add('visible');
        bottomNav.classList.add('visible');
      } else {
        sideNav.classList.remove('visible');
        bottomNav.classList.remove('visible');
      }
      var activeId = null;
      for(var i = all.length - 1; i >= 0; i--){
        var r = all[i].el.getBoundingClientRect();
        if(r.top <= 130 && r.bottom > 0){ activeId = all[i].el.id; break; }
      }
      if(!activeId && scrollY < 200 && all.length) activeId = all[0].el.id;
      if(activeId !== currentActive){
        currentActive = activeId;
        [sideNav, bottomNav].forEach(function(nav){
          nav.querySelectorAll('a').forEach(function(a){
            a.classList.toggle('active', a.getAttribute('data-target') === activeId);
          });
        });
        // 更新折叠状态下底部目录当前章节文本
        if(currentBtn && activeId){
          var activeNode = all.find(function(n){ return n.el.id === activeId; });
          currentBtn.textContent = activeNode ? clean(activeNode.text, 14) : '目录';
        }
        /* 断点与上方 CSS 一致：≤1628px 显示的是底部条而非侧目录 */
        if(activeId && window.innerWidth <= 1628){
          var activeLink = bottomNav.querySelector('a.active');
          if(activeLink){
            var nr = bottomNav.getBoundingClientRect();
            var lr = activeLink.getBoundingClientRect();
            if(lr.left < nr.left || lr.right > nr.right){
              activeLink.scrollIntoView({ behavior:'smooth', inline:'center', block:'nearest' });
            }
          }
        }
      }
      ticking = false;
    }
    window.addEventListener('scroll', function(){
      if(!ticking){ requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
    window.addEventListener('resize', function(){
      if(!ticking){ requestAnimationFrame(update); ticking = true; }
    });
    update();
  }

  if(document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', initSectionNav);
  } else {
    initSectionNav();
  }
})();

// ============================================================
// 区域K - 事件委托（替代内联事件处理器，配合 CSP 移除 'unsafe-inline'）
// 消费 data-nav / data-act / data-scroll / data-search-trigger
// 捕获阶段处理图片 onerror（隐藏 / 重试一次）
// ============================================================
(function(){
  // 点击委托：导航 / 行为 / 滚动 / 搜索触发
  document.addEventListener('click', function(e){
    var nav = e.target.closest('[data-nav]');
    if(nav){ location.href = nav.getAttribute('data-nav'); return; }

    var act = e.target.closest('[data-act]');
    if(act){
      var fn = act.getAttribute('data-act');
      if(fn === 'xwCopy'){ if(window.xwCopy) window.xwCopy(); return; }
      if(fn === 'doSearch'){ if(window.doSearch) window.doSearch(act.getAttribute('data-q') || ''); return; }
      if(window[fn]){ window[fn](act); return; } // toggleHomeSection/toggleCollapse/togglePitfall/openLightbox 收元素本身
    }

    var sc = e.target.closest('[data-scroll]');
    if(sc){ var t = document.getElementById(sc.getAttribute('data-scroll')); if(t) t.scrollIntoView({behavior:'smooth', block:'start'}); return; }

    var st = e.target.closest('[data-search-trigger]');
    if(st){ var b = document.getElementById('searchBtn'); if(b) b.click(); return; }
  });

  // 一键复制：覆盖 .r-copy 与任意非 .copy-btn 的 [data-copy-text]（.copy-btn 由上方既有委托处理）
  document.addEventListener('click', function(e){
    var btn = e.target.closest('.r-copy, [data-copy-text]:not(.copy-btn)');
    if(!btn) return;
    var text = btn.getAttribute('data-copy-text') || '';
    if(!text) return;
    function done(){ var o = btn.textContent; btn.textContent = '已复制 ✓'; btn.classList.add('copied'); setTimeout(function(){ btn.textContent = o; btn.classList.remove('copied'); }, 2000); }
    function fb(tx){ var ta = document.createElement('textarea'); ta.value = tx; ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0'; ta.setAttribute('readonly',''); document.body.appendChild(ta); var r = document.createRange(); r.selectNodeContents(ta); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); try{ document.execCommand('copy'); done(); }catch(x){} s.removeAllRanges(); document.body.removeChild(ta); }
    if(navigator.clipboard && navigator.clipboard.writeText){ navigator.clipboard.writeText(text).then(done).catch(function(){ fb(text); }); }
    else { fb(text); }
  });

  // 图片 onerror 捕获阶段处理（隐藏 / 重试一次），替代内联 onerror 属性
  document.addEventListener('error', function(e){
    var el = e.target;
    if(!el || el.tagName !== 'IMG') return;
    if(el.hasAttribute('data-hide-onerror')){ el.style.display = 'none'; return; }
    if(el.dataset.retry) return;
    el.dataset.retry = '1';
    var src = el.getAttribute('src') || '';
    var sep = src.indexOf('?') === -1 ? '?' : '&';
    el.src = src + sep + 'retry=' + Date.now();
  }, true);
})();

/* ============================================================================
   立体化 · 桌面端卡片「跟手 3D 倾斜」（2026-09-20 新增）
   ---------------------------------------------------------------------------
   只做一件事：把鼠标在卡片内的相对位置换算成 --tilt-x / --tilt-y 两个角度变量。
   真正的 transform 由 CSS 侧负责（见 style.css 第 4 节）：
     @media (hover:hover) and (pointer:fine){
       .card:hover{ transform: … rotateX(var(--tilt-y,0deg)) rotateY(var(--tilt-x,0deg)) }
     }
   🔴 变量名必须是 --tilt-x / --tilt-y，不能叫 --tx / --ty：
      style.css:62 里 `--tx: var(--text-color)` 是全站文字色的历史别名（被用 17 处），
      往卡片上写 --tx 会让「该卡片及其后代」的颜色变量解析成非法值（悬停时卡内文字变色）；
      而 JS 未写入时 rotateY(var(--tx)) 会把颜色当角度 → 整条 transform 失效回退 none。
   这样设计的好处：
     · 触屏完全不介入 —— 只有「有鼠标」的设备才走到这里，手机省电、不掉帧；
     · JS 失效时优雅降级 —— var(--tilt-x, 0deg) 取默认 0deg，卡片退化为「悬停上浮」，不会坏；
     · 系统开了「减少动态效果」则整段跳过。
   ============================================================================ */
(function(){
  try{
    if(!window.matchMedia) return;
    if(!window.matchMedia('(hover:hover) and (pointer:fine)').matches) return;
    if(window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    var SEL = '.card,.tile,.section-card,.lx-card,.upd-card,.hot-card';
    var cur = null;

    function clearTilt(el){
      if(!el) return;
      el.style.removeProperty('--tilt-x');
      el.style.removeProperty('--tilt-y');
    }

    document.addEventListener('pointermove', function(e){
      var el = (e.target && e.target.closest) ? e.target.closest(SEL) : null;
      if(el !== cur){ clearTilt(cur); cur = el; }
      if(!el) return;
      var r = el.getBoundingClientRect();
      if(!r.width || !r.height) return;
      var px = (e.clientX - r.left) / r.width;
      var py = (e.clientY - r.top) / r.height;
      // 最大倾角：横向 ±4°、纵向 ±3.5°，克制不晕
      el.style.setProperty('--tilt-x', ((px - 0.5) * 8).toFixed(2) + 'deg');
      el.style.setProperty('--tilt-y', ((0.5 - py) * 7).toFixed(2) + 'deg');
    }, { passive: true });

    // 指针离开文档（例如切到别的窗口）时归位，避免卡片保持歪着
    document.addEventListener('pointerleave', function(){
      clearTilt(cur); cur = null;
    }, true);
  }catch(err){ /* 静默失败：任何异常都不应影响站点其它功能 */ }
})();
;
/* ===== 首页动画效果 JavaScript ===== */

// 等待 DOM 加载完成
document.addEventListener('DOMContentLoaded', function() {

  // 存储所有 Observer 引用，用于清理
  const observers = [];

  /* 1. 滚动渐入动画 - 使用 IntersectionObserver */
  const fadeElements = document.querySelectorAll('.tile, .section-block, .home-collapsible');
  
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const fadeObserver = new IntersectionObserver(function(entries) {
    observers.push(fadeObserver);
    entries.forEach(function(entry, index) {
      if (entry.isIntersecting) {
        // 添加延迟，让卡片依次出现
        setTimeout(function() {
          entry.target.classList.add('visible');
        }, index * 100);
        fadeObserver.unobserve(entry.target);
      }
    });
  }, observerOptions);

  fadeElements.forEach(function(el) {
    el.classList.add('fade-in-up');
    fadeObserver.observe(el);
  });

  /* 2. 点击水波纹效果 - 同时支持鼠标和触摸 */
  function createRipple(e) {
    // 只在卡片和按钮上添加水波纹
    const target = e.target.closest('.tile, .btn, .icon-btn, .nav-links a');
    if (!target) return;

    // 防止重复创建
    const existingRipple = target.querySelector('.ripple');
    if (existingRipple) existingRipple.remove();

    const ripple = document.createElement('span');
    const rect = target.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    
    // 兼容触摸事件
    let x, y;
    if (e.touches) {
      x = e.touches[0].clientX - rect.left - size / 2;
      y = e.touches[0].clientY - rect.top - size / 2;
    } else {
      x = e.clientX - rect.left - size / 2;
      y = e.clientY - rect.top - size / 2;
    }

    ripple.style.cssText = `
      width: ${size}px;
      height: ${size}px;
      left: ${x}px;
      top: ${y}px;
    `;
    ripple.classList.add('ripple');

    target.style.position = 'relative';
    target.style.overflow = 'hidden';
    target.appendChild(ripple);

    setTimeout(function() {
      ripple.remove();
    }, 600);
  }

  // 同时监听 click 和 touchstart 事件
  document.addEventListener('click', createRipple);
  document.addEventListener('touchstart', createRipple, { passive: true });

  /* 3. 导航栏滚动效果 */
  const navbar = document.querySelector('.navbar');
  let lastScroll = 0;

  window.addEventListener('scroll', function() {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 50) {
      navbar.classList.add('scrolled');
    } else {
      navbar.classList.remove('scrolled');
    }
    
    lastScroll = currentScroll;
  });

  /* 4. 数字动态效果 - 访问量统计 */
  const counters = document.querySelectorAll('#busuanzi_value_site_pv, #busuanzi_value_site_uv');
  
  const counterObserver = new IntersectionObserver(function(entries) {
    observers.push(counterObserver);
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate');
        setTimeout(function() {
          entry.target.classList.remove('animate');
        }, 300);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  counters.forEach(function(counter) {
    counter.classList.add('counter');
    counterObserver.observe(counter);
  });

  /* 5. 主题色横条 - 动态添加到各板块 */
  const sections = document.querySelectorAll('.home-collapsible');
  
  sections.forEach(function(section) {
    const header = section.querySelector('.home-collapsible-header');
    if (header && !header.querySelector('.theme-color-bar')) {
      const bar = document.createElement('div');
      bar.classList.add('theme-color-bar');
      
      // 根据板块类型设置颜色
      const sectionId = section.id;
      if (sectionId.includes('herbs')) {
        bar.style.background = 'linear-gradient(90deg, #107c10, #4caf50)';
      } else if (sectionId.includes('life')) {
        bar.style.background = 'linear-gradient(90deg, #ff8c00, #ffb900)';
      } else if (sectionId.includes('tech')) {
        bar.style.background = 'linear-gradient(90deg, #0078d4, #4da6e8)';
      } else if (sectionId.includes('pop')) {
        bar.style.background = 'linear-gradient(90deg, #6b69d6, #9c27b0)';
      }
      
      header.insertBefore(bar, header.firstChild);
    }
  });

  /* 6. 平滑滚动增强 */
  document.querySelectorAll('a[href^="#"]').forEach(function(anchor) {
    anchor.addEventListener('click', function(e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
      }
    });
  });

  /* 7. 卡片点击反馈 - 触摸设备优化 */
  document.querySelectorAll('.tile').forEach(function(tile) {
    let isTouchDevice = 'ontouchstart' in window;
    
    if (isTouchDevice) {
      // 触摸设备：使用 touchstart 和 touchend
      tile.addEventListener('touchstart', function() {
        this.style.transform = 'translateY(-4px) scale(0.98)';
      });
      
      tile.addEventListener('touchend', function() {
        setTimeout(function() {
          tile.style.transform = '';
        }, 150);
      });
    } else {
      // 桌面设备：保留 hover 效果
      tile.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-8px) scale(1.02)';
      });
      
      tile.addEventListener('mouseleave', function() {
        this.style.transform = '';
      });
    }
  });

  /* 8. 数字滚动动画 - 从不蒜子获取真实数据 */
  function animateNumbers(targetValue, el) {
    const duration = 1500; // 1.5秒
    const step = targetValue / (duration / 16); // 60fps
    let current = 0;

    const timer = setInterval(function() {
      current += step;
      if (current >= targetValue) {
        current = targetValue;
        clearInterval(timer);
      }
      el.textContent = Math.floor(current);
    }, 16);
  }

  // 等待不蒜子数据加载（兼容 magazine 风格 .mag-stat-strip 和传统 .site-stats 两种布局）
  function waitForBusuanzi() {
    const pvEl = document.getElementById('busuanzi_value_site_pv');
    const uvEl = document.getElementById('busuanzi_value_site_uv');

    // 检查不蒜子是否已加载数据
    const hasPvData = pvEl && pvEl.textContent !== '' && pvEl.textContent !== '-' && pvEl.textContent !== '0';
    const hasUvData = uvEl && uvEl.textContent !== '' && uvEl.textContent !== '-' && uvEl.textContent !== '0';

    if (hasPvData || hasUvData) {
      // ===== 1. 更新 magazine 风格统计条（首页 .mag-stat-strip #magVisitorCount）=====
      const magVisitor = document.getElementById('magVisitorCount');
      if (magVisitor && hasUvData) {
        const uv = parseInt(uvEl.textContent.replace(/,/g, ''));
        if (!isNaN(uv) && uv > 0) {
          animateNumbers(uv, magVisitor);
        }
      }

      // ===== 2. 更新传统 site-stats 布局（.stat-number + 标签文字匹配）=====
      const statNumbers = document.querySelectorAll('.stat-number');
      statNumbers.forEach(function(el) {
        const label = el.nextElementSibling;
        if (label && label.textContent.includes('访问') && hasPvData) {
          const pv = parseInt(pvEl.textContent.replace(/,/g, ''));
          if (!isNaN(pv)) animateNumbers(pv, el);
        } else if (label && label.textContent.includes('访客') && hasUvData) {
          const uv = parseInt(uvEl.textContent.replace(/,/g, ''));
          if (!isNaN(uv)) animateNumbers(uv, el);
        }
      });
    } else {
      // 不蒜子未加载，500ms后重试（最多重试约30秒）
      if (!waitForBusuanzi._retries) waitForBusuanzi._retries = 0;
      waitForBusuanzi._retries++;
      if (waitForBusuanzi._retries < 60) {
        setTimeout(waitForBusuanzi, 500);
      } else {
        console.warn('⚠️ 不蒜子访客统计加载超时');
        var fallback = document.getElementById('magVisitorCount');
        if (fallback) fallback.style.opacity = '0.4';
      }
    }
  }

  // 进入视口时触发（兼容 .site-stats 和 .mag-stat-strip 两种布局）
  const statsObserver = new IntersectionObserver(function(entries) {
    observers.push(statsObserver);
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        // 开始等待不蒜子数据
        waitForBusuanzi();
        statsObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  const statsEl = document.querySelector('.site-stats') || document.querySelector('.mag-stat-strip');
  if (statsEl) statsObserver.observe(statsEl);

  /* 6. 板块/页面计数器动画 - 基于 data-target 属性 */
  const targetCounters = document.querySelectorAll('.stat-number[data-target]');
  
  const targetCounterObserver = new IntersectionObserver(function(entries) {
    observers.push(targetCounterObserver);
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        const el = entry.target;
        const target = parseInt(el.getAttribute('data-target'));
        if (!isNaN(target) && target > 0) {
          animateNumbers(target, el);
        }
        targetCounterObserver.unobserve(el);
      }
    });
  }, { threshold: 0.5 });

  targetCounters.forEach(function(counter) {
    targetCounterObserver.observe(counter);
  });

  // 页面卸载时清理所有 Observer（防止内存泄漏）
  window.addEventListener('pagehide', function() {
    observers.forEach(function(observer) {
      if (observer && typeof observer.disconnect === 'function') {
        observer.disconnect();
      }
    });
  });
});
;
/**
 * 自动新闻加载器
 * 根据当前页面自动加载对应的 *-news.json 文件并显示
 * 
 * 使用方式：
 *   1. 在页面中添加一个容器：<div id="autoNewsBody"></div>
 */

(function () {
  // 全局 API：折叠/展开 .home-collapsible 卡片
  // 委托入口在 app.js：点击 [data-act="toggleHomeSection"] 触发本函数
  // 复用 CSS 已就绪的 .open class 控制展开（grid-template-rows: 1fr），
  // 箭头由 CSS .home-collapsible.open .hc-arrow { transform: rotate(180deg) } 自动翻转
  window.toggleHomeSection = function (el) {
    var wrap = el && el.closest ? el.closest('.home-collapsible') : null;
    if (!wrap) return;
    wrap.classList.toggle('open');
  };

  // 全局 API：新闻条目「展开详情 / 收起详情」
  // 委托入口同样在 app.js：点击 [data-act="toggleNewsDetail"] 触发本函数（收按钮元素本身）。
  //
  // 🔴 显隐走 [hidden] **属性**，不走 class —— [hidden] 是 HTML 原生语义，
  //    屏幕阅读器靠它判断内容在不在，`aria-expanded` 也跟它对齐。
  //    代价是：style.css 里**不能**给 .news-detail 写 display（写了就把 [hidden] 顶掉、
  //    详情永远展着），必须写成 .news-detail[hidden]{display:none}。改样式时别踩。
  window.toggleNewsDetail = function (el) {
    if (!el || !el.closest) return;
    var box = el.closest('.news-content');
    var det = box ? box.querySelector('.news-detail') : null;
    if (!det) return;
    var willOpen = det.hasAttribute('hidden');        // 当前收着的 → 这一下要展开
    if (willOpen) { det.removeAttribute('hidden'); } else { det.setAttribute('hidden', ''); }
    el.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
    el.classList.toggle('is-open', willOpen);
    var txt = el.querySelector('.news-more-txt');
    if (txt) txt.textContent = willOpen ? '收起详情' : '展开详情';
  };

  // 页面 → JSON 文件映射
  const PAGE_MAP = {
    'bracelet':  'bracelet-news.json',
    'zisha':     'zisha-news.json',
    'console':   'console-news.json',
    'chinajoy':  'chinajoy-news.json',
    'tesla':     'tesla-news.json',
    'fsd':       'fsd-news.json',
    'health-tea': 'health-tea-news.json',
    'sheyang':   'sheyang-news.json',
    'marvel':   'marvel-news.json',
    'apple':    'apple-news.json',
  };

  // 获取当前页面对应的 JSON 文件
  function getJsonFile() {
    const path = window.location.pathname;
    const page = path.split('/').pop().replace('.html', '');
    return PAGE_MAP[page] || null;
  }

  // 安全转义：防止仓库/自动化被篡改时的存储型 XSS
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  // 行内 Markdown：先转义再替换，不引入 XSS 面（与 changelog.js 的 md() 同一套约定）。
  // 自动化写稿惯用 **加粗** 标关键词，旧版只转义不解析 → 页面上原样显示成刺眼的星号
  // （2026-09-22 修：全站 11 个 news JSON 共 900+ 处）。
  function md(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  }
  // 仅允许 http/https/mailto，阻断 javascript:/data: 等危险协议
  function safeUrl(u) {
    if (typeof u !== 'string') return '';
    return /^(https?:|mailto:)/i.test(u.trim()) ? u.trim() : '';
  }

  // 渲染新闻列表
  //
  // 2026-09-24 改版：条目从「一段长正文」变成「摘要常显 + 正文折叠」。
  //   起因：全站 11 个板块 88 条，正文平均 612 字、最长 2358 字，而自动化提示词
  //   要求的是「content(50-100字摘要)」，实测超了 6–23 倍 —— 读者点进板块页看到的是
  //   一篇篇改写过的新闻稿，而不是「今天发生了什么」。摘要 = 摆在明面的那段。
  //   兼容：老数据没有 summary 时整段 content 照旧当摘要显示、按钮不出现，
  //   所以存量新闻不用等全部补写完就能上线（补写见 scripts/guard_news_length.py）。
  function renderNews(container, news) {
    let html = '';
    news.forEach(function (item, idx) {
      let tagHtml = '';
      (item.tags || []).forEach(function (t) {
        tagHtml += '<span class="news-tag ' + esc(t.class || 'default') + '">' + esc(t.text) + '</span>';
      });
      let link = safeUrl(item.url)
        ? '<a href="' + esc(item.url) + '" target="_blank" rel="noopener" style="font-size:0.78rem;margin-left:6px;">🔗原文</a>'
        : '';

      // 摘要压成单行：摘要的定位是「一眼看完」，带换行会把它变成小正文
      var sum  = String(item.summary == null ? '' : item.summary).replace(/\s+/g, ' ').trim();
      var body = String(item.content == null ? '' : item.content).trim();
      // 正文比摘要长出 30 字以上才值得折 —— 不然点开只多一两行，白给一个按钮
      var hasDetail = !!(sum && body && body.length > sum.length + 30);
      var detailId = 'nd-' + idx;

      html += '<div class="news-item">' +
                '<div class="news-date">' + esc(item.date) + '</div>' +
                '<div class="news-content">' + tagHtml +
                  '<p class="news-sum">' + md(sum || body) + link + '</p>' +
                  (hasDetail
                    ? '<button class="news-more" type="button" aria-expanded="false" aria-controls="' + detailId +
                        '" data-act="toggleNewsDetail"><span class="news-more-txt">展开详情</span>' +
                        '<span class="news-more-arrow" aria-hidden="true"></span></button>' +
                      '<div class="news-detail" id="' + detailId + '" hidden>' + detailHtml(body) + '</div>'
                    : '') +
                '</div>' +
              '</div>';
    });
    container.innerHTML = html;
  }

  // 详情正文：按行拆段。自动化写稿里 6/88 条带换行（漫威那条是 `\n\n· **档期大盘**：…`
  // 的准列表写法），塞进单个 <p> 会被 HTML 折成一大坨 —— 折叠区本来就长，
  // 再不给分段等于把「点开看详情」做成「点开看墙」。单行的 82 条拆分后仍是一段，无变化。
  function detailHtml(s) {
    return String(s == null ? '' : s)
      .split(/\n+/)
      .map(function (line) { return line.trim(); })
      .filter(function (line) { return line; })
      .map(function (line) { return '<p>' + md(line) + '</p>'; })
      .join('');
  }

  // 「2026-09-23」→「今天 / 昨天 / 3 天前」。
  // 数据只有日期精度，相对天数就是它能给的唯一诚实表达；精确日期放 title 不丢信息。
  // 好处是跨天会自己变，用户开着页面过夜再切回来也是对的。
  function relDay(v) {
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(v == null ? '' : v));
    if (!m) return String(v == null ? '' : v);
    var t = new Date(+m[1], +m[2] - 1, +m[3]);
    if (isNaN(t.getTime())) return String(v);
    var n = new Date();
    var days = Math.round((new Date(n.getFullYear(), n.getMonth(), n.getDate()) - t) / 86400000);
    if (days <= 0) return '今天';
    if (days === 1) return '昨天';
    if (days < 30) return days + ' 天前';
    return m[2] + '-' + m[3];   // 太久远就退回日期，不硬凑「N 个月前」
  }

  // 主函数
  function loadAutoNews() {
    const jsonFile = getJsonFile();
    if (!jsonFile) return;  // 当前页面不需要自动新闻

    const container = document.getElementById('autoNewsBody');
    const countEl   = document.getElementById('autoNewsCount');
    if (!container) return;  // 页面没有容器

    fetch(jsonFile + '?t=' + Math.floor(Date.now() / 600000)) // 10 分钟窗口戳：同窗口内浏览器/CDN 直接命中缓存，不再每次击穿
      .then(function (r) {
        if (!r.ok) throw new Error('Not found');
        return r.json();
      })
      .then(function (data) {
        // 同步"最后更新时间"为新闻实际更新日期，避免与「实时」徽标矛盾。
        // 显示成相对天数（今天/昨天/N 天前）而不是死日期——死日期看着像静态快照，
        // 相对天数会自己跨天变化，且精确日期仍挂在 title 上。
        var updEl = document.getElementById('lastNewsUpdate');
        if (updEl && data.updated) {
          var paintUpd = function () {
            updEl.textContent = relDay(data.updated);
            updEl.title = '板块资讯更新日：' + data.updated;
          };
          paintUpd();
          // 页面开着过夜再切回来时要重算，否则会一直停在「今天」
          document.addEventListener('visibilitychange', function () {
            if (!document.hidden) paintUpd();
          });
        }
        if (!data.news || data.news.length === 0) return;
        if (countEl) countEl.textContent = data.news.length + '条';
        renderNews(container, data.news);
        // 显示整个折叠区域（保留 grid 折叠动画：display:grid + 添加 open 类）
        var wrapper = document.getElementById('hc-auto-news');
        if (wrapper) {
          wrapper.style.display = 'grid';
          wrapper.classList.add('open');
        }
      })
      .catch(function (e) {
        console.log('[auto_news] 加载失败:', jsonFile, e);
      });
  }

  // DOM 就绪后执行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadAutoNews);
  } else {
    loadAutoNews();
  }
})();
;
/**
 * daily-pick.js - 今日推荐 + 热门搜索
 * 本地图片 + 加载淡入动画
 */
(function () {
  // ===== 推荐池（本地图片，无外部依赖）=====
  // ⚠️ 每条的 img 必须与 name/url/desc 主题严格对应，禁止混用其它主题照片
  // （养生茶/天气/高考 三条因仓库无对应真实照片、且外网取图被限流，暂移除以杜绝错配）
  const pickPool = [
    {
      name: '特斯拉 Model Y',
      desc: '用车科普·充电指南·配件推荐一网打尽',
      tag: '🚗 数码科技',
      url: 'tesla.html',
      img: 'img/tesla/modely/front.webp'
    },
    {
      name: 'PlayStation 5',
      desc: '超高速SSD·DualSense手柄·次世代游戏体验',
      tag: '🎮 主机图鉴',
      url: 'console-playstation-5.html',
      img: 'img/consoles/ps5.webp'
    },
    {
      name: '紫砂壶鉴赏',
      desc: '95件紫砂艺术品，品味东方美学',
      tag: '🏺 传统文化',
      url: 'zisha.html',
      img: 'img/zisha/wht2026_p1_3.webp'
    },
    {
      name: 'Nintendo Switch 2',
      desc: '独占大作+多人派对，动森/塞尔达/马车8',
      tag: '🎮 主机图鉴',
      url: 'console-switch-2.html',
      img: 'img/consoles/switch-2.webp'
    }
  ];

  // ===== 热门搜索词 =====
  const hotKeywords = [
    'Model Y 充电攻略',
    '2026高考分数线',
    'PS5 必玩游戏',
    '漫威观影顺序',
    '紫砂壶怎么养',
    '文玩手串真假分辨',
    '射阳天气预报',
    'Switch 2 配置'
  ];

  // ===== 今日推荐逻辑 =====
  let currentPickIndex = -1;

  function renderPick(animate) {
    animate = (animate !== false);
    var card = document.getElementById('pick-card');
    if (!card) return;

    // 随机选一个（避免连续重复）
    var newIndex;
    do {
      newIndex = Math.floor(Math.random() * pickPool.length);
    } while (newIndex === currentPickIndex && pickPool.length > 1);
    currentPickIndex = newIndex;

    var item = pickPool[newIndex];

    if (animate) {
      card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      card.style.opacity = '0';
      card.style.transform = 'translateY(12px)';
    }

    // 更新内容
    card.href = item.url;
    card.target = '_self';
    card.onclick = null; // <a> 标签直接跳转，清除旧 JS

    var img = document.getElementById('pick-img');
    if (img) {
      img.src = item.img;
      img.alt = item.name;
      img.onerror = function() {
        // 本地图片加载失败，显示 emoji 占位
        this.style.display = 'none';
        var fb = document.createElement('div');
        fb.style.cssText = 'width:80px;height:80px;display:flex;align-items:center;justify-content:center;font-size:36px;background:var(--dark-tile);border-radius:8px;flex-shrink:0;';
        fb.textContent = item.tag.split(' ')[0];
        this.parentNode.insertBefore(fb, this.nextSibling);
      };
    }

    var nameEl = document.getElementById('pick-name');
    if (nameEl) nameEl.textContent = item.name;

    var descEl = document.getElementById('pick-desc');
    if (descEl) descEl.textContent = item.desc;

    var tagEl = document.getElementById('pick-tag');
    if (tagEl) tagEl.textContent = item.tag;

    if (animate) {
      var _card = card;
      setTimeout(function() {
        _card.style.opacity = '1';
        _card.style.transform = 'translateY(0)';
      }, 50);
    }
  }

  // ===== 热门搜索 =====
  function renderHotTags() {
    var container = document.getElementById('hot-tags');
    if (!container) return;
    container.innerHTML = hotKeywords.map(function(kw) {
      return '<a class="hot-tag" data-act="doSearch" data-q="' + kw + '">' + kw + '</a>';
    }).join('');
  }

  window.doSearch = function(kw) {
    var searchInput = document.getElementById('homeSearchInput');
    if (searchInput) {
      searchInput.value = kw;
      searchInput.focus();
      searchInput.dispatchEvent(new Event('input'));
      var hot = document.getElementById('search-hot');
      if (hot) hot.classList.remove('active');
    }
  };

  // ===== 初始化 =====
  function init() {
    renderPick(true); // 首次加载带淡入
    renderHotTags();

    var refreshBtn = document.getElementById('pick-refresh');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', function(e) {
        e.preventDefault();
        e.stopPropagation();
        var icon = this;

        // 按钮旋转动画
        icon.style.transition = 'transform 0.5s ease';
        icon.style.transform = 'rotate(360deg)';
        setTimeout(function() { icon.style.transform = ''; }, 500);

        var card = document.getElementById('pick-card');
        if (card) {
          card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
          card.style.opacity = '0';
          card.style.transform = 'translateY(10px)';
          setTimeout(function() {
            renderPick(false); // 内容替换
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
          }, 300);
        } else {
          renderPick(true);
        }
      });
    }

    // 搜索框聚焦/失焦
    var searchInput = document.getElementById('homeSearchInput');
    var searchHot = document.getElementById('search-hot');
    if (searchInput && searchHot) {
      searchInput.addEventListener('focus', function() { searchHot.classList.add('active'); });
      searchInput.addEventListener('blur', function() {
        setTimeout(function() { searchHot.classList.remove('active'); }, 200);
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
;
/**
 * home-feed.js — 首页「今日更新」+「热门精选」渲染
 *
 * 今日更新：聚合各板块最新新闻（/home-feed.json，由 scripts/build_home_feed.py 在部署前生成，
 *           CI 每次构建都会基于最新新闻重算，确保随自动化每天三班刷新而自动保鲜）。
 * 热门精选：编辑精选招牌专题（/hot-picks.json，均为仓库内真实封面图，严禁 AI 生成图）。
 *
 * 设计约束：
 *  - 首页直接读取静态 JSON，不并发拉 12 个 news 文件，降低请求数。
 *  - 10 分钟缓存窗口（?t=），避免 CDN/浏览器长期陈旧，又不过度频繁请求。
 *  - 任何加载失败均给出温和降级文案，不白屏。
 */
(function () {
  var CACHE = '?t=' + Math.floor(Date.now() / 600000); // 10 分钟窗口

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // 行内 Markdown：先转义再替换，不引入 XSS 面（与 changelog.js / auto_news_loader.js 同一套约定）。
  // 聚合进来的新闻正文带 **加粗** 标记，旧版只转义不解析 → 首页「今日更新」卡上会露出星号。
  function md(s) {
    return esc(s)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  }

  // 板块中文名 -> 本站板块页（点卡片跳转到这里；显示名与 scripts/build_home_feed.py 的 BOARD_FILES 一致）
  // 数据里没有自带板块页链接，故在此集中维护一份映射；板块稳定，新增板块时补一行即可。
  var BOARD_LINK = {
    '特斯拉': 'tesla.html',
    '特斯拉 FSD': 'tesla.html',
    '苹果新品': 'apple.html',
    '漫威宇宙': 'marvel.html',
    '养生茶': 'health-tea.html',
    '紫砂艺术': 'zisha.html',
    '文玩手串': 'bracelet.html',
    '射阳动态': 'sheyang.html',
    'ChinaJoy': 'chinajoy.html',
    '主机图鉴': 'console.html'
  };

  function renderToday(d) {
    var items = d && d.items ? d.items : (Array.isArray(d) ? d : []);
    var grid = document.getElementById('updGrid');
    if (!grid) return;
    if (!items || !items.length) {
      grid.innerHTML = '<div class="upd-card" style="grid-column:1/-1"><div class="upd-sum">各板块今日暂未抓取到新动态，自动化会在每天 08:00 / 14:00 / 21:00 自动补新。</div></div>';
      return;
    }
    grid.innerHTML = items.map(function (it) {
      // 整卡可点击跳转板块页：复用 app.js 全站通用的 [data-nav] 委托（点击最近带 data-nav 的祖先即跳转）
      var href = BOARD_LINK[it.board];
      var navAttr = href ? ' data-nav="' + esc(href) + '"' : '';
      // 「阅读原文」仍指向外部新闻源（新标签页打开）
      var link = it.url
        ? '<a class="upd-link" href="' + esc(it.url) + '" target="_blank" rel="noopener">阅读原文 →</a>'
        : '';
      return '<div class="upd-card" tabindex="0"' + navAttr + '>' +
        '<div class="upd-meta"><span class="upd-board">' + esc(it.board) + '</span>' +
        '<span class="upd-date">' + esc(it.date) + '</span></div>' +
        '<div class="upd-sum">' + md(it.content) + '</div>' + link +
        '</div>';
    }).join('');

    // 「阅读原文」外链：阻止冒泡，避免触发整卡 [data-nav] 跳转到板块页（否则点外链会先跳板块）
    Array.prototype.forEach.call(grid.querySelectorAll('.upd-link'), function (a) {
      a.addEventListener('click', function (e) { e.stopPropagation(); });
    });
    // 键盘可达：卡片本身获焦后回车 / 空格跳转到板块页；焦点在内链时不触发（上面已 stopPropagation 隔离）
    grid.addEventListener('keydown', function (e) {
      var card = e.target;
      if (!card || !card.classList || !card.classList.contains('upd-card') || !card.hasAttribute('data-nav')) return;
      if (e.key === 'Enter' || e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault();
        location.href = card.getAttribute('data-nav');
      }
    });
  }

  function renderPicks(d) {
    var items = d && d.items ? d.items : (Array.isArray(d) ? d : []);
    var grid = document.getElementById('hotGrid');
    if (!grid) return;
    if (!items || !items.length) {
      grid.innerHTML = '<article class="hot-card" style="grid-column:1/-1"><div class="hot-body"><div class="hot-title">精选筹备中</div><div class="hot-desc">编辑精选招牌专题即将上线。</div></div></article>';
      return;
    }
    grid.innerHTML = items.map(function (it) {
      var img = it.img
        ? '<img src="' + esc(it.img) + '" alt="' + esc(it.title) + '" loading="lazy" width="320" height="180">'
        : '';
      var tag = it.board
        ? '<span class="hot-pick-tag">编辑推荐 · ' + esc(it.board) + '</span>'
        : '<span class="hot-pick-tag">编辑推荐</span>';
      return '<article class="hot-card">' +
        '<a class="hot-thumb" href="' + esc(it.url) + '" aria-label="' + esc(it.title) + '">' + img + '</a>' +
        '<div class="hot-body">' +
        '<div class="hot-title"><a href="' + esc(it.url) + '">' + esc(it.title) + '</a></div>' +
        '<div class="hot-desc">' + esc(it.desc) + '</div>' + tag +
        '</div></article>';
    }).join('');
  }

  function loadJSON(url, ok) {
    fetch(url + CACHE)
      .then(function (r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
      .then(function (d) { ok(d); })
      .catch(function (e) { console.log('[home-feed] 加载失败:', url, e); });
  }

  function init() {
    loadJSON('/home-feed.json', renderToday);
    loadJSON('/hot-picks.json', renderPicks);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
;
/**
 * solar-term.js — 首页「节气钟」
 * 按日期算当前 24 节气 + 距下一节气倒计时 + 当日物候/一句/香事。
 * 算法：21 世纪寿星公式，y=年份后两位，L=floor(y/4)，±1 天误差（显示标“约”）。
 * 纯客户端，无依赖、无后端。
 */
(function () {
  var TERMS = ['小寒', '大寒', '立春', '雨水', '惊蛰', '春分', '清明', '谷雨',
    '立夏', '小满', '芒种', '夏至', '小暑', '大暑', '立秋', '处暑',
    '白露', '秋分', '寒露', '霜降', '立冬', '小雪', '大雪', '冬至'];
  var C = [5.4055, 20.12, 3.87, 18.73, 5.63, 20.646, 4.81, 20.1, 5.52, 21.04,
    5.678, 21.37, 7.108, 22.83, 7.5, 23.13, 7.646, 23.042, 8.318, 23.438,
    7.438, 22.36, 7.18, 21.94];
  var MONTH = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10, 11, 11, 12, 12];

  var INFO = {
    '立春': { phen: '东风解冻 · 蛰虫始振 · 鱼陟负冰', poem: '律回岁晚冰霜少，春到人间草木知', inc: '焚甘松，启户迎新' },
    '雨水': { phen: '獭祭鱼 · 候雁北 · 草木萌动', poem: '随风潜入夜，润物细无声', inc: '煮雨前茶，配淡淡白檀' },
    '惊蛰': { phen: '桃始华 · 仓庚鸣 · 鹰化为鸠', poem: '微雨众卉新，一雷惊蛰始', inc: '焚艾草，驱晦醒神' },
    '春分': { phen: '玄鸟至 · 雷乃发声 · 始电', poem: '仲春初四日，春色正中分', inc: '焚玫瑰檀，调和肝脾' },
    '清明': { phen: '桐始华 · 田鼠化鴽 · 虹始见', poem: '清明时节雨纷纷', inc: '焚柏子，清心明志' },
    '谷雨': { phen: '萍始生 · 鸣鸠拂羽 · 戴胜降桑', poem: '谷雨春光晓，山川黛色青', inc: '焙新茶，配清茶尾韵' },
    '立夏': { phen: '蝼蝈鸣 · 蚯蚓出 · 王瓜生', poem: '绿树阴浓夏日长', inc: '焚薄荷配檀，清暑' },
    '小满': { phen: '苦菜秀 · 靡草死 · 麦秋至', poem: '小满江河易满', inc: '焚藿香，化湿和中' },
    '芒种': { phen: '螳螂生 · 鵙始鸣 · 反舌无声', poem: '时雨及芒种，四野皆插秧', inc: '田家焚艾，驱虫祈丰' },
    '夏至': { phen: '鹿角解 · 蜩始鸣 · 半夏生', poem: '昼晷已云极，宵漏自此长', inc: '焚香，静心避暑' },
    '小暑': { phen: '温风至 · 蟋蟀居壁 · 鹰始鸷', poem: '倏忽温风至，因循小暑来', inc: '焚清香，纳凉读史' },
    '大暑': { phen: '腐草为萤 · 土润溽暑 · 大雨时行', poem: '桂轮开子夜，萤火照空时', inc: '焚龙涎，化湿醒神' },
    '立秋': { phen: '凉风至 · 白露降 · 寒蝉鸣', poem: '一叶梧桐一报秋', inc: '焚桂花沉，迎秋' },
    '处暑': { phen: '鹰乃祭鸟 · 天地始肃 · 禾乃登', poem: '离离暑云散，袅袅凉风起', inc: '焚菊檀，肃净心神' },
    '白露': { phen: '鸿雁来 · 玄鸟归 · 群鸟养羞', poem: '蒹葭苍苍，白露为霜', inc: '焚白檀，润燥' },
    '秋分': { phen: '雷始收声 · 蛰虫坯户 · 水始涸', poem: '金气秋分，风清露冷秋期半', inc: '焚香，平分昼夜' },
    '寒露': { phen: '鸿雁来宾 · 雀入水为蛤 · 菊有黄华', poem: '袅袅凉风动，凄凄寒露零', inc: '焚茱萸配沉，暖身' },
    '霜降': { phen: '豺乃祭兽 · 草木黄落 · 蛰虫咸俯', poem: '霜叶红于二月花', inc: '焚桂皮香，温中' },
    '立冬': { phen: '水始冰 · 地始冻 · 雉入大水', poem: '冻笔新诗懒写，寒炉美酒时温', inc: '焚香，围炉' },
    '小雪': { phen: '虹藏不见 · 天气上升 · 闭塞成冬', poem: '久雨重阳后，清寒小雪前', inc: '焚甘松，温室' },
    '大雪': { phen: '鹖鴠不鸣 · 虎始交 · 荔挺出', poem: '夜深知雪重，时闻折竹声', inc: '焚暖香，御寒' },
    '冬至': { phen: '蚯蚓结 · 麋角解 · 水泉动', poem: '天时人事日相催，冬至阳生春又来', inc: '焚香，一阳来复' },
    '小寒': { phen: '雁北乡 · 鹊始巢 · 雉始雊', poem: '小寒料峭，一番春意换年芳', inc: '围炉焚沉，静待春信' },
    '大寒': { phen: '鸡始乳 · 征鸟厉疾 · 水泽腹坚', poem: '旧雪未及消，新雪又拥户', inc: '煮茶配檀，岁末清供' }
  };

  function termDate(year, n) {
    var y = year % 100;
    var day = Math.floor(y * 0.2422 + C[n - 1]) - Math.floor(y / 4);
    return new Date(year, MONTH[n - 1] - 1, day);
  }

  function pad(d) { return (d < 10 ? '0' : '') + d; }
  function fmt(dt) { return dt.getFullYear() + '.' + pad(dt.getMonth() + 1) + '.' + pad(dt.getDate()); }

  function render() {
    var el = document.getElementById('solarTerm');
    if (!el) return;

    var now = new Date();
    var y = now.getFullYear();
    var dates = [];
    for (var i = 1; i <= 24; i++) dates.push(termDate(y, i));

    var cur = 23;
    for (var i = 0; i < 24; i++) { if (dates[i] <= now) cur = i; }

    var curName, curDate, nextName, nextDate;
    if (cur >= 0 && dates[cur] <= now) {
      curName = TERMS[cur]; curDate = dates[cur];
      var ni = cur + 1;
      if (ni < 24) { nextName = TERMS[ni]; nextDate = dates[ni]; }
      else { nextName = TERMS[0]; nextDate = termDate(y + 1, 1); }
    } else {
      curName = TERMS[23]; curDate = termDate(y - 1, 24);
      nextName = TERMS[0]; nextDate = dates[0];
    }

    var days = Math.ceil((nextDate - now) / 86400000);
    var info = INFO[curName] || { phen: '', poem: '', inc: '' };

    el.innerHTML =
      '<div class="st-term">' + curName + '</div>' +
      '<div class="st-sub">' + fmt(curDate) + ' – ' + fmt(nextDate) + '（约）</div>' +
      '<div class="st-count">距 <b>' + nextName + '</b> 还有 <b>' + days + '</b> 天</div>' +
      '<div class="st-phen">' + info.phen + '</div>' +
      '<div class="st-poem">「' + info.poem + '」</div>' +
      '<div class="st-inc">香事 · ' + info.inc + '</div>';
  }

  if (document.readyState !== 'loading') render();
  else document.addEventListener('DOMContentLoaded', render);
})();
;
/**
 * daily-item.js — 首页「每日一物」
 * 按日期确定性轮换展示一个国风知识卡（紫砂/养生/文玩），
 * 同一天所有人看到同一物；可点「换一个」临时随机。
 */
(function () {
  var ITEMS = [
    { name: '紫砂 · 紫泥', cat: '紫砂', one: '沉稳温润，最宜泡茶的骨', detail: '紫泥透气而不渗，养久生包浆。一把好壶，是岁月与手掌共同写就。' },
    { name: '紫砂 · 朱泥', cat: '紫砂', one: '红润细腻，扬香利器', detail: '朱泥密度高、聚香好，最宜乌龙、高香红茶，出汤利落。' },
    { name: '紫砂 · 段泥', cat: '紫砂', one: '清雅米黄，显汤色', detail: '段泥砂质疏朗，宜绿茶、白茶，茶汤清亮，壶色也养得干净。' },
    { name: '文玩 · 星月菩提', cat: '文玩', one: '盘玩见性的修行物件', detail: '星月菩提盘久开片、挂瓷包浆，急不得——像许多事，慢即是快。' },
    { name: '养生 · 节气茶饮', cat: '养生', one: '顺时而饮，比进补更要紧', detail: '春饮花、夏饮绿、秋饮青、冬饮红。顺着节气喝茶，身体自有主张。' },
  ];

  function dayIndex() {
    var d = new Date();
    var key = Math.floor(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / 86400000);
    return ((key % ITEMS.length) + ITEMS.length) % ITEMS.length;
  }

  function card(it) {
    return '<div class="di-cat">' + it.cat + '</div>' +
      '<div class="di-name">' + it.name + '</div>' +
      '<div class="di-one">' + it.one + '</div>' +
      '<div class="di-detail">' + it.detail + '</div>' +
      '<button class="di-shuffle" id="dailyShuffle">换一个 ↻</button>';
  }

  function render(seed) {
    var el = document.getElementById('dailyItem');
    if (!el) return;
    var i;
    if (typeof seed === 'number') i = seed;
    else i = dayIndex();
    el.innerHTML = card(ITEMS[i]);
  }

  function init() {
    render();
    document.addEventListener('click', function (e) {
      var b = e.target && e.target.closest && e.target.closest('#dailyShuffle');
      if (b) {
        var r = Math.floor(Math.random() * ITEMS.length);
        render(r);
      }
    });
  }

  if (document.readyState !== 'loading') init();
  else document.addEventListener('DOMContentLoaded', init);
})();
;
(function () {
  'use strict';

  var ROTATE_MS = 7000;

  function ready(fn) {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', fn);
    } else { fn(); }
  }

  function init() {
    var hero = document.querySelector('.lx-hero');
    var link = document.getElementById('heroLink');
    var imgA = document.getElementById('heroImgA');
    var imgB = document.getElementById('heroImgB');
    var kicker = document.getElementById('heroKicker');
    var title = document.getElementById('heroTitle');
    var sub = document.getElementById('heroSub');
    var cta = document.getElementById('heroCta');
    var dotsWrap = document.getElementById('heroDots');
    if (!hero || !link || !imgA || !imgB || !dotsWrap) return;

    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    fetch('/hero.json', { cache: 'no-cache' })
      .then(function (r) { if (!r.ok) throw new Error('bad'); return r.json(); })
      .then(function (d) {
        var slides = d && d.slides ? d.slides : (Array.isArray(d) ? d : []);
        if (!slides || !slides.length) throw new Error('empty');
        setup(slides);
      })
      .catch(function () { /* 拉取失败则保留静态首屏，不报错 */ });

    function setup(slides) {
      // 预加载全部图片，避免切换时闪烁
      slides.forEach(function (s) { var im = new Image(); im.src = s.img; });

      var idx = 0;
      var cur = imgA, nxt = imgB; // 两层交替
      var timer = null;
      var hovering = false;

      slides.forEach(function (s, i) {
        var b = document.createElement('button');
        b.className = 'lx-hero-dot' + (i === 0 ? ' is-active' : '');
        b.type = 'button';
        b.setAttribute('role', 'tab');
        b.setAttribute('aria-label', (s.kicker || ('专题 ' + (i + 1))));
        b.addEventListener('click', function (e) { e.preventDefault(); go(i, true); });
        dotsWrap.appendChild(b);
      });
      var dots = dotsWrap.querySelectorAll('.lx-hero-dot');

      function apply(s) {
        link.setAttribute('href', s.link || '#');
        link.setAttribute('aria-label', (s.kicker || '') + (s.title ? '：' + s.title : ''));
        kicker.textContent = s.kicker || '';
        title.textContent = s.title || '';
        sub.textContent = s.sub || '';
        cta.textContent = s.cta || '查看专题 →';
        if (cur) cur.setAttribute('alt', (s.kicker || s.title || ''));
      }

      function swap() {
        nxt.classList.add('is-active');
        cur.classList.remove('is-active');
        var t = cur; cur = nxt; nxt = t; // 交换：cur 始终为可见层
      }

      function paint(s) {
        apply(s);
        if (reduce) {
          nxt.src = s.img; swap(); return;
        }
        nxt.removeAttribute('src');
        nxt.src = s.img;
        if (nxt.decode) {
          nxt.decode().then(swap).catch(swap);
        } else {
          nxt.onload = swap; nxt.onerror = swap;
        }
      }

      function go(n, manual) {
        n = (n + slides.length) % slides.length;
        if (n === idx) return;
        idx = n;
        paint(slides[idx]);
        for (var i = 0; i < dots.length; i++) {
          dots[i].classList.toggle('is-active', i === idx);
        }
        if (manual) restart();
      }

      function start() {
        if (timer || hovering || document.hidden) return;
        timer = setInterval(function () { go(idx + 1); }, ROTATE_MS);
      }
      function stop() { if (timer) { clearInterval(timer); timer = null; } }
      function restart() { stop(); start(); }

      hero.addEventListener('mouseenter', function () { hovering = true; stop(); });
      hero.addEventListener('mouseleave', function () { hovering = false; start(); });
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) stop(); else start();
      });
      // 首屏即启动自动轮播
      start();
    }
  }

  ready(init);
})();
;
(function () {
  'use strict';

  // 首页滚动渐显：为关键区块/卡片自动注入 .reveal，IntersectionObserver 触发 .in
  // 注意：.lx-hero 不在观察列表——首屏 hero 必须无条件可见，绝不依赖本脚本
  // （2026-08-19：hero 曾显式带 reveal，脚本失效时整块保持 opacity:0，露出页面背景空洞）
  var selectors = '.lx-vol, .lx-mod, .lx-deck .lx-card, .upd-card, .hot-card, .sheyang-card, .lx-vital, .lx-masthead';

  function init() {
    var nodes = document.querySelectorAll(selectors);
    nodes.forEach(function (el) { el.classList.add('reveal'); });

    if (!('IntersectionObserver' in window)) {
      nodes.forEach(function (el) { el.classList.add('in'); });
      return;
    }

    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          obs.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -50px 0px', threshold: 0.1 });

    nodes.forEach(function (el) { obs.observe(el); });

    // 兜底：页面 load 后 1s，已进入视口却仍未显形的元素强制加 .in
    // 防 IO 回调异常/竞争导致内容永久隐藏（视觉退化为直接可见，绝不留空洞）
    function forceInView() {
      nodes.forEach(function (el) {
        if (el.classList.contains('in')) return;
        var r = el.getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) el.classList.add('in');
      });
    }
    if (document.readyState === 'complete') {
      setTimeout(forceInView, 1000);
    } else {
      window.addEventListener('load', function () { setTimeout(forceInView, 1000); });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
;
/**
 * status-bubble.js - 龙兄状态气泡 + 近期动态新鲜度标签
 *
 * 逻辑：
 * 1. 优先读取 status.json → 显示今日状态（手动更新）
 * 2. 回退：status.json 无数据或过期 → 读 data/updates.json 最新板块
 * 3. 近期动态列表始终来自 data/updates.json
 */
(function () {
  // 计算时间差，返回友好的描述
  function getTimeAgo(dateStr) {
    if (!dateStr) return '';
    var now = new Date();
    var date = new Date(dateStr);
    var diff = now - date;
    var days = Math.floor(diff / (1000 * 60 * 60 * 24));
    var hours = Math.floor(diff / (1000 * 60 * 60));
    var minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 60) {
      return minutes <= 0 ? '刚刚' : minutes + '分钟前';
    } else if (hours < 24) {
      return hours + '小时前';
    } else if (days < 30) {
      return days + '天前';
    } else {
      return dateStr;
    }
  }

  // 计算新鲜度等级
  function getFreshnessLevel(dateStr) {
    if (!dateStr) return 'old';
    var now = new Date();
    var date = new Date(dateStr);
    var diff = now - date;
    var days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days <= 3) return 'fresh-3days';
    if (days <= 7) return 'fresh-week';
    return 'old';
  }

  // 状态是否过期：手写状态超过 3 天就不再当"今日状态"展示，
  // 改由 updates.json 的最新板块动态顶上（兑现文件头注释里"过期回退"的承诺）
  var STATUS_TTL_MS = 3 * 24 * 60 * 60 * 1000;
  function isStale(data) {
    if (!data) return true;
    var ts = data.updatedAt || data.timestamp || '';
    if (!ts) return false;              // 没有时间戳的老数据不判过期，照常显示
    var d = new Date(ts);
    if (isNaN(d.getTime())) return false;
    return (new Date() - d) > STATUS_TTL_MS;
  }

  // 获取基础路径
  function getBasePath() {
    var base = '';
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var m = scripts[i].src.match(/(.*\/)js\/.+/);
      if (m) { base = m[1]; break; }
    }
    return base;
  }

  // 显示状态气泡（来自 status.json）
  function showStatusBubble(data) {
    var statusInline = document.getElementById('todayStatusInline');
    if (statusInline) statusInline.style.display = 'flex';

    var statusText = document.getElementById('todayStatusText');
    var bubbleDate = document.getElementById('bubbleDate');
    var bubbleTime = document.getElementById('bubbleTime');

    // 兼容两种数据格式：
    // - data/status.json（Hugo模板注入）：有 timestamp，无顶层 date/updatedAt
    // - static/status.json（fetch回退）：有 date/time/updatedAt
    var ts = data.timestamp || data.updatedAt || '';
    var dateStr = data.date || (ts ? ts.split('T')[0] : '');
    var updatedAtStr = data.updatedAt || ts;

    if (statusText) statusText.textContent = data.status || '';
    if (bubbleDate) bubbleDate.textContent = dateStr;
    if (bubbleTime) bubbleTime.textContent = getTimeAgo(updatedAtStr);

    // 同时更新杂志布局中的状态显示
    var magStatus = document.getElementById('magStatus');
    if (magStatus) {
      var base = (data.status || '') + ' ' + (data.emoji || '');
      if (data.dnd) {
        magStatus.innerHTML = base + ' <span class="lx-dnd-badge" style="display:inline-flex;align-items:center;gap:3px;margin-left:6px;padding:1px 7px;border-radius:999px;font-size:.66rem;font-weight:700;background:rgba(229,57,53,.14);color:#e53935;border:1px solid rgba(229,57,53,.4);letter-spacing:.02em;vertical-align:middle;">🔕 勿扰</span>';
        magStatus.classList.add('lx-dnd');
      } else {
        magStatus.textContent = base;
      }
    }
  }

  // 回退：从 updates.json 找最新板块显示
  function fallbackToLatestUpdate(data) {
    var latestUpdate = null;
    var latestDate = null;

    for (var key in data) {
      if (data[key] && data[key].lastUpdate) {
        var updateDate = new Date(data[key].lastUpdate);
        if (!latestDate || updateDate > latestDate) {
          latestDate = updateDate;
          latestUpdate = data[key];
          latestUpdate.name = key;
        }
      }
    }

    if (latestUpdate) {
      showStatusBubble({
        status: '最近在折腾「' + latestUpdate.name + '」板块 🛠️',
        date: latestUpdate.lastUpdate,
        updatedAt: latestUpdate.lastUpdate
      });
    }
  }

  // 加载近期动态列表（来自 data/updates.json）
  function loadUpdatesList(data) {
    var updateList = document.getElementById('updateLogList');
    if (!updateList) return;

    var updates = [];
    for (var key in data) {
      if (data[key] && data[key].lastUpdate) {
        updates.push({
          name: key,
          url: data[key].url,
          lastUpdate: data[key].lastUpdate
        });
      }
    }
    updates.sort(function (a, b) {
      return new Date(b.lastUpdate) - new Date(a.lastUpdate);
    });
    updates = updates.slice(0, 6);

    var html = '';
    updates.forEach(function (item) {
      var freshness = getFreshnessLevel(item.lastUpdate);
      var timeAgo = getTimeAgo(item.lastUpdate);

      var badge = '';
      if (freshness === 'fresh-3days') {
        badge = '<span class="fresh-dot"></span>';
      } else if (freshness === 'fresh-week') {
        badge = '<span class="new-badge">新</span>';
      } else {
        badge = '<span style="width:8px;height:8px;flex-shrink:0;"></span>';
      }

      html += '<div class="update-item">' + badge +
        '<a href="' + item.url + '" class="update-text" style="text-decoration:none;color:inherit;">' + item.name + '</a>' +
        '<span class="update-time">' + timeAgo + '</span></div>';
    });

    updateList.innerHTML = html;
  }

  // 主入口：优先读HTML内联的状态数据（构建时注入，无缓存问题）；
  // 若无内联数据（旧版静态页），再回退到 fetch status.json
  function loadStatusAndUpdates() {
    var base = getBasePath();

    // 1. 优先读取构建时注入的 #site-status-data（不走网络，彻底规避微信缓存）
    var embedded = document.getElementById('site-status-data');
    if (embedded && embedded.textContent) {
      try {
        var data = JSON.parse(embedded.textContent);
        if (data && data.status) {
          if (isStale(data)) {
            // 手写状态超过 3 天：不再冒充"今日状态"，回退到最新板块动态
            fallbackXhr(base);
          } else {
            showStatusBubble(data);
          }
          loadUpdatesListFromUrl(base); // 近期动态仍从 updates.json 读取
          return;
        }
      } catch (e) {
        // 解析失败，继续走 fetch 回退
      }
    }

    // 2. 回退：fetch status.json（加时间戳破微信浏览器缓存）
    var statusXhr = new XMLHttpRequest();
    statusXhr.open('GET', base + 'status.json?t=' + Math.floor(Date.now() / 600000), true);
    statusXhr.responseType = 'json';
    statusXhr.setRequestHeader('Cache-Control', 'no-cache');

    statusXhr.onload = function () {
      if (statusXhr.status === 200 && statusXhr.response && statusXhr.response.status) {
        if (isStale(statusXhr.response)) {
          // 手写状态超过 3 天，回退到最新板块动态
          fallbackXhr(base);
        } else {
          showStatusBubble(statusXhr.response);
        }
      } else {
        // status.json 无数据，回退到 updates.json
        fallbackXhr(base);
      }
      // 无论 status.json 是否成功，都加载近期动态列表
      loadUpdatesListFromUrl(base);
    };

    statusXhr.onerror = function () {
      fallbackXhr(base);
      loadUpdatesListFromUrl(base);
    };

    statusXhr.send();
  }

  // 回退：读取 updates.json 找最新板块
  function fallbackXhr(base) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/updates.json', true);
    xhr.responseType = 'json';
    xhr.onload = function () {
      if (xhr.status === 200 && xhr.response) {
        fallbackToLatestUpdate(xhr.response);
      }
    };
    xhr.send();
  }

  // 加载近期动态列表
  function loadUpdatesListFromUrl(base) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/updates.json', true);
    xhr.responseType = 'json';
    xhr.onload = function () {
      if (xhr.status === 200 && xhr.response) {
        loadUpdatesList(xhr.response);
      }
    };
    xhr.send();
  }

  // 页面加载完成后执行
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadStatusAndUpdates);
  } else {
    loadStatusAndUpdates();
  }
})();
;
/**
 * updates.js - 板块最后更新日期
 */
(function () {
  function loadUpdates() {
    var containers = document.querySelectorAll('[data-update-key]');
    if (!containers.length) return;

    var base = '';
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
      var m = scripts[i].src.match(/(.*\/)js\/.+/);
      if (m) { base = m[1]; break; }
    }

    var xhr = new XMLHttpRequest();
    xhr.open('GET', base + 'data/updates.json', true);
    xhr.responseType = 'json';
    xhr.onload = function () {
      if (xhr.status !== 200) return;
      var data = xhr.response;
      if (!data) return;

      containers.forEach(function (el) {
        var key = el.getAttribute('data-update-key');
        var info = data[key];
        if (info && info.lastUpdate) {
          el.textContent = '最后更新：' + info.lastUpdate;
          el.style.display = 'block';
        }
      });
    };
    xhr.send();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadUpdates);
  } else {
    loadUpdates();
  }
})();
;
/*
 * auto-collapse.js — 通用「板块 > 阈值条数则默认折叠」组件
 *
 * 两种启用方式：
 *  1) 显式：在容器加 data-ac 及下列属性（手动控制，优先级最高）。
 *  2) 自动：脚本扫描全站「带标题的内容网格 / 列表 / section」，只­要直接子项 > 阈值（默认 2）即自动折叠。
 *           适用于所有页面，无需逐页加标记；新增页面亦自动生效。
 *
 * 显式属性：
 *   data-ac                    开启自动折叠
 *   data-ac-body=".sel"        折叠区选择器（默认：自身或首个匹配）
 *   data-ac-items=".sel"       计数与折叠判定的子项选择器（默认 :scope > *）
 *   data-ac-head=".sel"        点击折叠的头部选择器 / 标签
 *   data-ac-threshold="2"      超过该条数才折叠（默认 2）
 *   data-ac-default="auto|open|collapsed"  默认状态；auto=超过阈值才折叠（默认）
 *   data-ac-count="true|false" 是否显示条数徽标（默认 true）
 *
 * 自动探测规则（autoDetect）：
 *   - 候选：含 grid/deck/board/gallery/list 类名的容器，或直接包含 ≥(阈值+1) 张「卡片」的 div/section/ul/ol。
 *   - 头部：容器「前一个兄弟」中的标题（h2–h6 或 .section-title/.section-header/.sec-title 等），必须位于容器之外。
 *   - 排除：nav/header/footer/aside/工具栏/面包屑/hero/kpi，以及旅行加密相册页。
 *   - 找不到标题的板块静默跳过（不折叠），避免破坏布局。
 */
(function () {
  'use strict';

  var THRESHOLD = 2;

  // 标题节点：仅 h2–h6 或带标题语义 class 的元素（不含 h1，避免折叠页面主标题下的首要内容）
  function isHeadingNode(n) {
    if (!n) return false;
    if (/^H[2-6]$/.test(n.tagName)) return true;
    var c = (n.className || '');
    if (typeof c !== 'string') return false;
    return /(sec-title|section-title|section-header|section-head|sec-header|heading|title|\bhead\b)/i.test(c);
  }

  // 是否为「内容块」而非裸标题：遇到内容块即停止向上寻找标题
  function looksLikeContentBlock(n) {
    if (!n) return false;
    if (/^H[1-6]$/.test(n.tagName)) return false;
    return !!(n.children && n.children.length >= 1 && !isHeadingNode(n));
  }

  // 在上下文中寻找首个标题元素（含 h2–h6 或带标题语义 class 的容器）
  function firstHeadingIn(ctx) {
    if (!ctx || !ctx.querySelector) return null;
    return ctx.querySelector('h2,h3,h4,h5,h6,.section-title,.section-header,.sec-title,.sec-header,.cat-header,[class*="sec-title"],[class*="heading"]');
  }

  // 返回元素所属「语义区块」：最近的 section/main/article 或带容器语义的类。
  // 用于把 findHead 的标题探测限定在本区块内，杜绝折叠键错挂到外层/无关 section 的标题
  // （万年历·拼假攻略误挂整年视图即用旧版跨区块攀爬所致）。
  function enclosingSection(el) {
    var a = el;
    while (a) {
      if (a.tagName === 'SECTION' || a.tagName === 'MAIN' || a.tagName === 'ARTICLE') return a;
      var c = (a.className || '');
      if (typeof c === 'string' && /(^|\s)(container|lx-section|cal-page|cat-section|board-section)(\s|$)/.test(c)) return a;
      a = a.parentElement;
    }
    return null;
  }

  // 仅返回位于容器之外的标题（保证折叠容器时标题仍可见）
  function findHead(board) {
    var sec = enclosingSection(board);
    // 1) 在 board 所属区块内，向上遍历前一个兄弟，直到标题
    var prev = board.previousElementSibling;
    while (prev && prev !== sec) {
      if (isHeadingNode(prev)) return prev;
      var inner = firstHeadingIn(prev); // 标题被包在 header 容器里（如 .cat-header > h2）
      if (inner) return inner;
      prev = prev.previousElementSibling;
    }
    // 2) 父级的前一个兄弟链，但**不超过本区块边界**（不向上爬到外层 section 的标题）
    var p = board.parentElement;
    while (p && p !== sec) {
      var pp = p.previousElementSibling;
      while (pp && pp !== sec) {
        if (isHeadingNode(pp)) return pp;
        var inner2 = firstHeadingIn(pp);
        if (inner2) return inner2;
        pp = pp.previousElementSibling;
      }
      p = p.parentElement;
    }
    return null;
  }

  var EXCLUDE_SEL = 'nav,header,footer,aside,.navbar,.sidebar,.breadcrumb,.pagination,.toolbar,.toc,.bm-bar,.quick-toc';
  var SKIP_CLASS = /(nav|menu|breadcrumb|toolbar|pagination|footer|sidebar|hero|kpi|crumb|social|share|bread|skip|toc|bookmark|fab|float|banner|ad-|advert|modal|popup|overlay)/i;

  function isExcluded(board) {
    if (board.closest && board.closest(EXCLUDE_SEL)) return true;
    var c = board.className || '';
    if (typeof c === 'string' && SKIP_CLASS.test(c)) return true;
    return false;
  }

  // 卡片判定：class 含 "card" 子串、且不是容器（grid/deck/board/gallery/list）的 token，
  // 才视为卡片。这样可精确命中 *-card / card-* 等卡片类，又不会把 .cj-era-grid 的内部 div
  // 或 .card-grid 容器误判为卡片。
  function isCard(ch) {
    if (!ch.classList) return false;
    var toks = ch.classList;
    for (var i = 0; i < toks.length; i++) {
      var t = toks[i].toLowerCase();
      if (t.indexOf('card') > -1 && !/(grid|deck|board|gallery|list)/.test(t)) return true;
    }
    return false;
  }

  function collectItems(board) {
    var out = [];
    var kids = board.children;
    var bcn = (typeof board.className === 'string') ? board.className : '';
    // 仅当列表容器带 grid/deck/board/gallery/list 类名时才计 li，避免折叠文章正文里的普通 markdown 项目符号列表
    var isCardList = /(^|[\s-])(grid|deck|board|gallery|list)([\s-]|$)/i.test(bcn);
    for (var i = 0; i < kids.length; i++) {
      var ch = kids[i];
      if (!ch.classList) continue;
      if (isCard(ch)) out.push(ch);
      else if (ch.tagName === 'LI' && isCardList) out.push(ch); // 仅列表型容器才计 li
      else if (ch.tagName === 'ARTICLE' && isCard(ch)) out.push(ch); // 仅卡片型 article
    }
    return out;
  }

  function makeBoard(board, opts) {
    var body = opts.body || board;
    var head = opts.head || null;
    var itemSel = opts.itemSel || ':scope > *';
    var threshold = (typeof opts.threshold === 'number') ? opts.threshold : THRESHOLD;
    var def = opts.def || 'auto';
    var showCount = (opts.count !== false);

    var items = (itemSel === ':scope > *')
      ? Array.prototype.slice.call(body.children)
      : body.querySelectorAll(itemSel);
    var count = items.length;

    var collapsed;
    if (def === 'open') collapsed = false;
    else if (def === 'collapsed') collapsed = true;
    else collapsed = count > threshold;

    // 自动模式且未超阈值：保持展开、不加折叠控件
    if (def === 'auto' && count <= threshold) {
      board.setAttribute('data-ac-state', 'open');
      return;
    }

    // 防错挂：找不到标题（如板块标题在本区块外）则不折叠，避免把 toggle 挂到卡片/容器上
    if (!head) {
      board.setAttribute('data-ac-state', 'open');
      return;
    }
    // 防与原生 <details>/<summary> 折叠控件重叠
    if (head.closest && head.closest('summary')) {
      board.setAttribute('data-ac-state', 'open');
      return;
    }
    // 防空板：body 无实质内容时不建折叠键（点了也看不见效果，属「没用」的一类）
    var bodyText = (body.innerText || '').trim();
    if (body.children.length === 0 && bodyText.length === 0) {
      board.setAttribute('data-ac-state', 'open');
      return;
    }

    board.classList.add('lx-ac');
    body.classList.add('lx-ac-body');
    head.classList.add('lx-ac-head', 'lx-ac-head-click');

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'lx-ac-toggle';
    toggle.setAttribute('aria-expanded', 'false');
    toggle.innerHTML =
      (showCount ? '<span class="lx-ac-count"></span>' : '') +
      '<span class="lx-ac-label"></span>' +
      '<span class="lx-ac-arrow" aria-hidden="true"></span>';

    var label = toggle.querySelector('.lx-ac-label');
    var arrow = toggle.querySelector('.lx-ac-arrow');
    var countBadge = toggle.querySelector('.lx-ac-count');

    function setState(state) {
      board.setAttribute('data-ac-state', state);
      var isOpen = state === 'open';
      toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      label.textContent = isOpen ? '收起' : '展开';
      arrow.textContent = isOpen ? '▴' : '▾';
      if (countBadge) countBadge.textContent = String(count);
    }

    head.appendChild(toggle);
    setState(collapsed ? 'collapsed' : 'open');

    function toggleState() {
      setState(board.getAttribute('data-ac-state') === 'open' ? 'collapsed' : 'open');
    }
    toggle.addEventListener('click', function (e) {
      e.stopPropagation();
      toggleState();
    });
    head.addEventListener('click', function (e) {
      if (e.target.closest && e.target.closest('.lx-ac-toggle')) return;
      toggleState();
    });
  }

  // 显式 data-ac 处理
  function initExplicit() {
    var boards = document.querySelectorAll('[data-ac]');
    Array.prototype.forEach.call(boards, function (board) {
      var bodySel = board.getAttribute('data-ac-body');
      var body = bodySel ? board.querySelector(bodySel) : null;
      if (bodySel && !body && board.matches(bodySel)) body = board; // body 即自身（无包裹模式）
      if (!body) body = board;

      var itemSel = board.getAttribute('data-ac-items') || ':scope > *';
      var headSel = board.getAttribute('data-ac-head');
      var head = null;
      if (headSel) {
        head = board.querySelector(headSel);
        if (!head && board.previousElementSibling && board.previousElementSibling.matches &&
            board.previousElementSibling.matches(headSel)) {
          head = board.previousElementSibling; // 头部为前一个兄弟节点（无包裹模式）
        }
      }
      if (!head) head = board.firstElementChild;
      if (!head) head = board;

      makeBoard(board, {
        body: body,
        head: head,
        itemSel: itemSel,
        threshold: parseInt(board.getAttribute('data-ac-threshold') || String(THRESHOLD), 10),
        def: board.getAttribute('data-ac-default') || 'auto',
        count: (board.getAttribute('data-ac-count') || 'true') !== 'false'
      });
    });
  }

  // 全站自动探测
  function autoDetect() {
    if (/travel/i.test(location.pathname)) return; // 旅行加密相册不自动处理

    var handled = new Set();
    // 显式板块及其所有后代不再自动处理
    document.querySelectorAll('[data-ac]').forEach(function (b) {
      handled.add(b);
      var d = b.querySelectorAll('*');
      Array.prototype.forEach.call(d, function (x) { handled.add(x); });
    });

  function fold(el) {
    // 跳过原生 <details> 折叠容器，避免与 <summary> 冲突
    if (el.closest && el.closest('details')) return;
    var items = collectItems(el);
    if (items.length <= THRESHOLD) return;
    var head = findHead(el);
    if (!head) return;
      // 防碰撞：同一标题已被另一折叠板占用（出现双 toggle），本容器不再挂键，
      // 避免一个标题下叠两个折叠键（如光辉电力·产品体系全覆盖内两兄弟卡片组共享同一 h2）
      if (head.querySelector('.lx-ac-toggle')) return;
      makeBoard(el, { body: el, head: head, itemSel: ':scope > *', threshold: THRESHOLD, def: 'auto', count: true });
      // 标记自身及祖先为已处理，避免外层容器重复折叠（仅折叠最内层板块）
      var a = el;
      while (a) { handled.add(a); a = a.parentElement; }
    }

    // 候选 1：带网格/列表语义类名的容器
    var named = document.querySelectorAll('[class*="grid"],[class*="deck"],[class*="board"],[class*="gallery"],[class*="list"]');
    Array.prototype.forEach.call(named, function (el) {
      if (handled.has(el) || isExcluded(el)) return;
      fold(el);
    });

    // 候选 2：直接包含多张卡片的 div/section/ul/ol（覆盖无 grid 类名的卡片列表）
    var broad = document.querySelectorAll('div,section,ul,ol');
    Array.prototype.forEach.call(broad, function (el) {
      if (handled.has(el) || isExcluded(el)) return;
      fold(el);
    });
  }

  function expandTarget(id) {
    if (!id) return;
    var el = document.getElementById(id);
    if (!el) return;
    var board = el.hasAttribute('data-ac') ? el : (el.closest ? el.closest('[data-ac]') : null);
    if (board) board.setAttribute('data-ac-state', 'open');
  }

  function initAutoCollapse() {
    initExplicit();
    autoDetect();

    // 页内锚点 / # 直达：自动展开目标板块
    document.addEventListener('click', function (e) {
      var a = e.target.closest && e.target.closest('a[href^="#"]');
      if (!a) return;
      var href = a.getAttribute('href');
      if (href && href.length > 1) expandTarget(decodeURIComponent(href.slice(1)));
    });
    if (location.hash && location.hash.length > 1) {
      setTimeout(function () { expandTarget(decodeURIComponent(location.hash.slice(1))); }, 0);
    }
  }

  if (document.readyState !== 'loading') initAutoCollapse();
  else document.addEventListener('DOMContentLoaded', initAutoCollapse);
})();
;
/* =============================================================
 * 通用倒计时组件（与任意页面解耦，不依赖万年历 lunar 引擎）
 * 用法：在任意元素上加 data-countdown，并指定一种目标：
 *   data-target="2026-10-01"              绝对日期（单值）
 *   data-annual="10-01"                   每年重复的 MM-DD（取下一个未到来的）
 *   data-dates="2027-02-06,2028-01-26"     显式候选列表（按时间取首个未到来的；适合春节/端午/中秋等农历浮动节日）
 * 可选属性：
 *   data-label="距国庆"   前缀文案（缺省不显示）
 *   data-past="已结束"    目标已过期时的文案（缺省"已结束"）
 *   data-zero="今天"      目标为今天时的文案（缺省"今天"）
 *   data-format="num"     仅输出数字（适用于外层已自备标签/单位的场景）
 * 渲染：默认输出 <span class="cd-label">…</span><b class="cd-num">N</b><span class="cd-unit">天</span>
 * 更新：加载时计算一次，并每 60 秒校准（跨天自动刷新）。
 * ============================================================= */
(function () {
  'use strict';

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function startOfToday() {
    var n = new Date();
    return new Date(n.getFullYear(), n.getMonth(), n.getDate());
  }

  // 解析候选目标日期（绝对或列表），返回「今天及以后」中最接近的一个
  function resolveTarget(el) {
    var now = startOfToday();
    var dates = [];

    // 单值绝对日期（首页近期节点：data/festivals.json 驱动，每个节日一个具体发生日）
    if (el.hasAttribute('data-date')) {
      var sd = parseISO(el.getAttribute('data-date').trim());
      if (sd) {
        if (sd < now) return { date: sd, passed: true };
        return { date: sd, passed: false };
      }
    } else if (el.hasAttribute('data-dates')) {
      el.getAttribute('data-dates').split(',').forEach(function (s) {
        var p = s.trim(); if (!p) return;
        var t = parseISO(p); if (t) dates.push(t);
      });
    } else if (el.hasAttribute('data-annual')) {
      var md = el.getAttribute('data-annual').trim();
      var m = parseInt(md.slice(0, 2), 10), d = parseInt(md.slice(3, 5), 10);
      var y = now.getFullYear();
      var cand = new Date(y, m - 1, d);
      if (cand < now) cand = new Date(y + 1, m - 1, d);
      dates.push(cand);
    } else if (el.hasAttribute('data-target')) {
      var t2 = parseISO(el.getAttribute('data-target').trim());
      if (t2) dates.push(t2);
    }

    if (!dates.length) return null;
    dates.sort(function (a, b) { return a - b; });
    for (var i = 0; i < dates.length; i++) {
      if (dates[i] >= now) return { date: dates[i], passed: false };
    }
    return { date: dates[dates.length - 1], passed: true }; // 全部已过期
  }

  function parseISO(s) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    if (!m) return null;
    return new Date(+m[1], +m[2] - 1, +m[3]);
  }

  function daysBetween(target) {
    var ms = target.getTime() - startOfToday().getTime();
    return Math.round(ms / 86400000);
  }

  function render(el) {
    var r = resolveTarget(el);
    if (!r) {
      el.textContent = '—';
      return;
    }
    // 已过期节日：隐藏节点（首页 data/festivals.json 由二米每日刷新剔除，这里为兜底，避免缓存窗口内残留）
    if (r.passed) {
      el.style.display = 'none';
      el._cdDiff = -1;
      return;
    }
    var target = r.date;
    var diff = daysBetween(target);
    el._cdDiff = diff; // 缓存剩余天数，供容器排序使用
    var label = el.getAttribute('data-label') || '';
    var past = el.getAttribute('data-past') || '已结束';
    var zero = el.getAttribute('data-zero') || '今天';
    var fmt = el.getAttribute('data-format') || '';

    if (diff < 0) {
      if (fmt === 'num') { el.textContent = past; }
      else { el.innerHTML = (label ? '<span class="cd-label">' + label + '</span>' : '') + '<span class="cd-end">' + past + '</span>'; }
      el.classList.add('cd-passed');
      el.classList.remove('is-soon');
      return;
    }
    if (diff === 0) {
      if (fmt === 'num') { el.textContent = zero; }
      else { el.innerHTML = (label ? '<span class="cd-label">' + label + '</span>' : '') + '<b class="cd-num">' + zero + '</b>'; }
      el.classList.remove('cd-passed', 'is-soon');
      return;
    }
    if (fmt === 'num') {
      el.textContent = String(diff);
    } else {
      el.innerHTML = (label ? '<span class="cd-label">' + label + '</span>' : '') +
        '<b class="cd-num">' + diff + '</b><span class="cd-unit">天</span>';
    }
    el.classList.remove('cd-passed');
    el.classList.toggle('is-soon', diff <= 30);
  }

  // 可选能力：容器加 data-countdown-sort 后，按剩余天数升序重排子节点
  // （最近优先；已过期节点沉底）。不影响未开启该特性的页面。
  function sortNodeContainers() {
    var containers = document.querySelectorAll('[data-countdown-sort]');
    for (var c = 0; c < containers.length; c++) {
      var box = containers[c];
      var kids = [];
      for (var k = 0; k < box.children.length; k++) {
        var ch = box.children[k];
        if (ch.hasAttribute && ch.hasAttribute('data-countdown')) kids.push(ch);
      }
      if (kids.length < 2) continue;
      kids.sort(function (a, b) {
        var da = (a._cdDiff == null ? Infinity : (a._cdDiff < 0 ? Infinity : a._cdDiff));
        var db = (b._cdDiff == null ? Infinity : (b._cdDiff < 0 ? Infinity : b._cdDiff));
        return da - db;
      });
      for (var n = 0; n < kids.length; n++) box.appendChild(kids[n]); // 按序 append = 重排
    }
  }

  function init() {
    var els = document.querySelectorAll('[data-countdown]');
    for (var i = 0; i < els.length; i++) render(els[i]);
    sortNodeContainers();
    // 跨天校准（渲染 + 重排，保证跨天后顺序依旧最近优先）
    setInterval(function () {
      for (var j = 0; j < els.length; j++) render(els[j]);
      sortNodeContainers();
    }, 60000);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
