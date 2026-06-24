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

// 3. 在线状态徽章
(function(){
  var badge=document.getElementById('statusBadge');
  if(!badge)return;
  function updateStatus(){
    var h=new Date().getHours();
    var isOnline=(h>=7&&h<23);
    badge.className='status-badge '+(isOnline?'online':'offline');
    badge.innerHTML=(isOnline?'🟢 站长在线':'🌙 站长已休息');
  }
  updateStatus();
  setInterval(updateStatus,60000);
})();

// 5. 今日龙兄在干嘛
(function(){
  var el=document.getElementById('todayStatus');
  if(!el)return;
  fetch('status.json?v='+Date.now())
    .then(function(r){if(!r.ok)throw new Error('Not found');return r.json();})
    .then(function(data){
      if(data&&data.message){
        el.innerHTML='<div class="ts-content">'+data.message+'</div>';
        if(data.date){
          el.innerHTML+='<div class="status-refresh-time">更新于 '+data.date+'</div>';
        }
      }else{
        el.innerHTML='<div class="ts-empty">暂无动态</div>';
      }
    })
    .catch(function(){
      el.innerHTML='<div class="ts-empty">暂无动态</div>';
    });
})();

// 4. 实时时钟（在天气页面初始化）
window.initClock=function(){
  var el=document.getElementById('liveClock');
  if(!el)return;
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

})();
