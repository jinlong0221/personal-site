/**
 * 龙兄知识库 · 全局 JavaScript
 * 纯原生，无框架依赖
 */
(function(){
'use strict';

// XSS Protection
function escapeHtml(t){
  if(!t)return'';
  var d=document.createElement('div');
  d.textContent=t;
  return d.innerHTML;
}

// 1. Theme Toggle
var THEME_KEY='theme';
function getAutoTheme(){var h=new Date().getHours();return(h>=6&&h<18)?'light':'dark';}
function applyTheme(t){
  document.documentElement.setAttribute('data-theme',t);
  localStorage.setItem(THEME_KEY,t);
  var btn=document.getElementById('themeToggle');
  if(btn){
    var sun=btn.querySelector('.icon-sun'),moon=btn.querySelector('.icon-moon');
    if(sun&&moon){sun.style.display=t==='dark'?'inline':'none';moon.style.display=t==='dark'?'none':'inline';}
  }
}
(function initTheme(){
  var saved=localStorage.getItem(THEME_KEY);
  applyTheme((saved==='dark'||saved==='light')?saved:getAutoTheme());
  var btn=document.getElementById('themeToggle');
  if(btn)btn.addEventListener('click',function(){
    var cur=document.documentElement.getAttribute('data-theme')||'dark';
    applyTheme(cur==='dark'?'light':'dark');
  });
  // Also handle #tb button for legacy compat
  var tb=document.getElementById('tb');
  if(tb)tb.addEventListener('click',function(){
    var cur=document.documentElement.getAttribute('data-theme')||'dark';
    applyTheme(cur==='dark'?'light':'dark');
  });
  if(typeof MutationObserver!=='undefined')
    new MutationObserver(function(){
      var t=document.documentElement.getAttribute('data-theme')||'dark';
      var btn=document.getElementById('themeToggle');
      if(btn){var sun=btn.querySelector('.icon-sun'),moon=btn.querySelector('.icon-moon');if(sun&&moon){sun.style.display=t==='dark'?'inline':'none';moon.style.display=t==='dark'?'none':'inline';}}
    }).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});
})();

// 2. Hamburger Menu
(function(){
  var hb=document.querySelector('.hamburger'),mn=document.querySelector('.mobile-nav');
  if(!hb||!mn)return;
  hb.addEventListener('click',function(){hb.classList.toggle('active');mn.classList.toggle('open');});
  mn.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){hb.classList.remove('active');mn.classList.remove('open');});});
  document.addEventListener('click',function(e){if(!hb.contains(e.target)&&!mn.contains(e.target)){hb.classList.remove('active');mn.classList.remove('open');}});
})();

// 3. Breadcrumb
(function(){
  var c=document.getElementById('breadcrumb');if(!c)return;
  var path=window.location.pathname;
  var parts=path.replace(/\/$/,'').split('/').filter(Boolean);
  var titleMap={
    'agarwood':'沉香鉴别','bracelet':'文玩手串','herbs':'中药材与香料',
    'sheyang':'射阳天气','tesla':'新能源汽车','travel':'旅行攻略',
    'tools':'工具箱','changelog':'更新日志','index':'首页',
    'diguniu':'地牯牛','dilong':'地龙','huashicao':'化石草',
    'huashifen':'滑石粉','jiangzhenxiang':'降真香','maoshikafei':'猫屎咖啡',
    'shuizhi':'水蛭','wulingzhi':'五灵脂','xiongdan':'熊胆',
    'model3':'Model 3','modely':'Model Y','models':'Model S','modelx':'Model X',
    'cybertruck':'赛博皮卡','charging':'充电指南','accessories':'车载配件','maintenance':'保养维修',
    'fengyan':'凤眼菩提','longyan':'龙眼菩提','magu':'麻古菩提',
    'mengma':'猛犸','pinxiang':'品香','quanao':'拳脑','wuxing':'五行','xingyue':'星月菩提','zijinboyu':'紫金钵鱼'
  };
  var crumbs=[{label:'首页',url:'index.html'}];
  for(var i=0;i<parts.length;i++){
    var name=parts[i].replace(/\.html?$/i,'');
    if(name==='index')continue;
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

// 4. Copy Buttons
document.addEventListener('click',function(e){
  var btn=e.target.closest('.copy-btn');if(!btn)return;
  var target=btn.getAttribute('data-copy-target');
  var text=target?(document.querySelector(target)||{}).textContent||'':btn.getAttribute('data-copy-text')||'';
  if(!text)return;
  function done(){btn.textContent='已复制 ✓';btn.classList.add('copied');setTimeout(function(){btn.textContent='复制';btn.classList.remove('copied');},2000);}
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done).catch(function(){var ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();try{document.execCommand('copy');done();}catch(x){}document.body.removeChild(ta);});}
  else{var ta=document.createElement('textarea');ta.value=text;ta.style.position='fixed';ta.style.left='-9999px';document.body.appendChild(ta);ta.select();try{document.execCommand('copy');done();}catch(x){}document.body.removeChild(ta);}
});

// Auto add copy buttons to code blocks & info boxes
function autoCopyButtons(){
  document.querySelectorAll('pre').forEach(function(b){
    if(b.parentElement.classList.contains('code-block-wrapper'))return;
    var w=document.createElement('div');w.className='code-block-wrapper';w.style.position='relative';
    b.parentNode.insertBefore(w,b);w.appendChild(b);
    var btn=document.createElement('button');btn.className='copy-btn code-copy-btn';btn.textContent='📋 复制';
    btn.setAttribute('data-copy-text',b.textContent||'');
    btn.style.cssText='position:absolute;top:8px;right:8px;z-index:10;';w.appendChild(btn);
  });
  document.querySelectorAll('.tip-box,.warning-box').forEach(function(box){
    if(box.querySelector('.copy-btn'))return;
    var btn=document.createElement('button');btn.className='copy-btn box-copy-btn';btn.textContent='复制';
    btn.setAttribute('data-copy-text',box.textContent||'');
    btn.style.cssText='position:absolute;bottom:8px;right:8px;z-index:10;font-size:0.75rem;padding:4px 10px;';
    box.style.position='relative';box.appendChild(btn);
  });
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',autoCopyButtons);else autoCopyButtons();

// 5. Search
var searchIndex=[];
function loadSearchIndex(){
  var base=window.location.pathname.replace(/[^/]*\.html?$/,'');
  fetch(base+'search-index.json').then(function(r){return r.json();}).then(function(d){searchIndex=d||[];}).catch(function(){});
}
function performSearch(q){
  if(!q||q.length<1)return[];
  var terms=q.toLowerCase().trim().split(/\s+/);
  return searchIndex.map(function(item){
    var pool=(item.title||'').toLowerCase()+' '+(item.keywords||'').toLowerCase()+' '+(item.description||'').toLowerCase();
    var score=0;terms.forEach(function(t){if(pool.indexOf(t)!==-1){score+=(item.title||'').toLowerCase().indexOf(t)!==-1?3:(item.description||'').toLowerCase().indexOf(t)!==-1?2:1;}});
    return{item:item,score:score};
  }).filter(function(r){return r.score>0;}).sort(function(a,b){return b.score-a.score;}).map(function(r){return r.item;});
}
function ensureSearchModal(){
  var ex=document.getElementById('searchModal');if(ex)return ex;
  var m=document.createElement('div');m.id='searchModal';m.className='search-modal';
  m.innerHTML='<div class="search-modal-content"><div class="search-modal-header"><input type="text" class="search-modal-input" placeholder="搜索药材、手串、车型..." aria-label="搜索"><button class="search-modal-close" aria-label="关闭">&times;</button></div><div class="search-modal-results"></div></div>';
  document.body.appendChild(m);return m;
}
(function(){
  loadSearchIndex();
  var modal=ensureSearchModal();
  var input=modal.querySelector('.search-modal-input');
  var results=modal.querySelector('.search-modal-results');
  var closeBtn=modal.querySelector('.search-modal-close');

  function open(q){
    modal.classList.add('active');
    setTimeout(function(){input.focus();if(q){input.value=q;handle(input.value);}},50);
  }
  function close(){modal.classList.remove('active');input.value='';results.innerHTML='';}
  function handle(q){
    if(q.length<1){results.innerHTML='<div class="search-hint">输入关键词开始搜索</div>';return;}
    var r=performSearch(q);
    if(r.length===0){results.innerHTML='<div class="search-no-results">没有找到相关内容</div>';return;}
    var h='<div class="search-results-list">';
    r.forEach(function(item){
      var desc=item.description||'';
      h+='<a href="'+escapeHtml(item.url)+'" class="search-result-item"><div class="search-result-title">'+escapeHtml(item.title)+'</div>'+(desc?'<div class="search-result-desc">'+escapeHtml(desc)+'</div>':'')+'</a>';
    });
    h+='</div>';results.innerHTML=h;
  }

  var sb=document.getElementById('searchBtn');if(sb)sb.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();open();});
  var hi=document.getElementById('homeSearchInput'),hb=document.getElementById('homeSearchBtn');
  if(hi&&hb){hb.addEventListener('click',function(){open(hi.value);});hi.addEventListener('keydown',function(e){if(e.key==='Enter')open(hi.value);});}
  var dt=null;input.addEventListener('input',function(){clearTimeout(dt);dt=setTimeout(function(){handle(input.value);},150);});
  if(closeBtn)closeBtn.addEventListener('click',function(e){e.preventDefault();close();});
  modal.addEventListener('click',function(e){if(e.target===modal)close();});
  document.addEventListener('keydown',function(e){if(e.key==='Escape'&&modal.classList.contains('active'))close();});
  results.innerHTML='<div class="search-hint">输入关键词开始搜索</div>';
})();

// 6. Guestbook (访客留言 + XSS过滤)
(function(){
  var form=document.getElementById('guestbookForm');
  var list=document.getElementById('guestbookList');
  if(!form||!list)return;

  var STORAGE_KEY='guestbook_msgs';

  function loadMsgs(){
    try{return JSON.parse(localStorage.getItem(STORAGE_KEY))||[];}catch(e){return[];}
  }
  function saveMsgs(msgs){localStorage.setItem(STORAGE_KEY,JSON.stringify(msgs));}

  function renderMsgs(){
    var msgs=loadMsgs();
    if(msgs.length===0){list.innerHTML='<p style="color:var(--text-muted);font-size:0.9rem;text-align:center;padding:20px;">暂无留言，来做第一个留言的访客吧 🐉</p>';return;}
    var html='';
    msgs.slice().reverse().forEach(function(m){
      html+='<div class="guest-msg"><div class="guest-msg-name">'+escapeHtml(m.name)+'</div><div class="guest-msg-text">'+escapeHtml(m.text)+'</div><div class="guest-msg-time">'+escapeHtml(m.time)+'</div></div>';
    });
    list.innerHTML=html;
  }

  form.addEventListener('submit',function(e){
    e.preventDefault();
    var name=(document.getElementById('guestName').value||'').trim().substring(0,20)||'匿名龙友';
    var text=(document.getElementById('guestMsg').value||'').trim().substring(0,500);
    if(!text){alert('请输入留言内容');return;}
    // XSS is handled by escapeHtml in renderMsgs
    var msgs=loadMsgs();
    msgs.push({name:name,text:text,time:new Date().toLocaleString('zh-CN')});
    saveMsgs(msgs);
    document.getElementById('guestName').value='';
    document.getElementById('guestMsg').value='';
    renderMsgs();
  });

  renderMsgs();
})();

// 7. Fade-in animation on scroll
(function(){
  var items=document.querySelectorAll('.card,.tile,.method-tile,.step-tile,.phase-tile,.log-item,.timeline-item');
  if(!items.length)return;
  if(!('IntersectionObserver' in window)){items.forEach(function(el){el.classList.add('visible');});return;}
  var obs=new IntersectionObserver(function(entries){
    entries.forEach(function(entry){if(entry.isIntersecting){entry.target.classList.add('visible');obs.unobserve(entry.target);}});
  },{threshold:0.1});
  items.forEach(function(el){obs.observe(el);});
})();

})();
