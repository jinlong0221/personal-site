/**
 * 龙兄知识库 · 全局 JavaScript v2
 * 纯原生，无框架依赖
 * 重写搜索：全站内容匹配 + 当前页高亮段落
 */
(function(){
'use strict';

// ========== XSS Protection ==========
function escapeHtml(t){
  if(!t)return'';
  var d=document.createElement('div');
  d.textContent=t;
  return d.innerHTML;
}

// ========== 1. Theme Toggle ==========
var THEME_KEY='theme';
function getAutoTheme(){var h=new Date().getHours();return(h>=6&&h<18)?'light':'dark';}
function applyTheme(t){
  document.documentElement.setAttribute('data-theme',t);
  localStorage.setItem(THEME_KEY,t);
  updateThemeIcon(t);
}
function updateThemeIcon(t){
  var btn=document.getElementById('themeToggle');
  if(!btn)return;
  var sun=btn.querySelector('.icon-sun'),moon=btn.querySelector('.icon-moon');
  if(sun&&moon){sun.style.display=t==='dark'?'inline':'none';moon.style.display=t==='dark'?'none':'inline';}
}
(function initTheme(){
  var saved=localStorage.getItem(THEME_KEY);
  var theme=(saved==='dark'||saved==='light')?saved:getAutoTheme();
  applyTheme(theme);
  var btn=document.getElementById('themeToggle');
  if(btn)btn.addEventListener('click',function(){
    var cur=document.documentElement.getAttribute('data-theme')||'dark';
    applyTheme(cur==='dark'?'light':'dark');
  });
  // Legacy #tb compat
  var tb=document.getElementById('tb');
  if(tb)tb.addEventListener('click',function(){
    var cur=document.documentElement.getAttribute('data-theme')||'dark';
    applyTheme(cur==='dark'?'light':'dark');
  });
})();

// ========== 2. Hamburger Menu ==========
(function(){
  var hb=document.querySelector('.hamburger');
  var mn=document.querySelector('.mobile-nav');
  if(!hb)return;
  // If no mobile-nav element exists, create one dynamically
  if(!mn){
    mn=document.createElement('div');
    mn.className='mobile-nav';
    mn.id='mobileNav';
    // Build links from existing nav-links
    var navLinks=document.querySelector('.nav-links');
    if(navLinks){
      var links=navLinks.querySelectorAll('a');
      links.forEach(function(a){
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
  mn.querySelectorAll('a').forEach(function(a){a.addEventListener('click',function(){hb.classList.remove('active');mn.classList.remove('open');});});
  document.addEventListener('click',function(e){if(!hb.contains(e.target)&&!mn.contains(e.target)){hb.classList.remove('active');mn.classList.remove('open');}});
})();

// ========== 3. Breadcrumb ==========
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
  // Determine base path for links
  var depth=parts.length-1; // how many dirs deep (last part is filename)
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

// ========== 4. Copy Buttons ==========
function copyText(text,btn){
  function done(){btn.textContent='已复制 ✓';btn.classList.add('copied');setTimeout(function(){btn.textContent='复制';btn.classList.remove('copied');},2000);}
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(text).then(done).catch(function(){fallbackCopy(text,done);});
  }else{fallbackCopy(text,done);}
}
function fallbackCopy(text,done){
  var ta=document.createElement('textarea');ta.value=text;ta.style.cssText='position:fixed;left:-9999px;top:-9999px;opacity:0';ta.setAttribute('readonly','');
  document.body.appendChild(ta);
  var range=document.createRange();range.selectNodeContents(ta);
  var sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);
  try{document.execCommand('copy');done();}catch(x){}
  sel.removeAllRanges();document.body.removeChild(ta);
}

document.addEventListener('click',function(e){
  var btn=e.target.closest('.copy-btn');if(!btn)return;
  var target=btn.getAttribute('data-copy-target');
  var text=target?(document.querySelector(target)||{}).textContent||'':btn.getAttribute('data-copy-text')||'';
  if(!text)return;
  copyText(text,btn);
});

// Auto-add copy buttons
function autoCopyButtons(){
  document.querySelectorAll('pre').forEach(function(b){
    if(b.parentElement.classList.contains('code-block-wrapper'))return;
    var w=document.createElement('div');w.className='code-block-wrapper';w.style.position='relative';
    b.parentNode.insertBefore(w,b);w.appendChild(b);
    var btn=document.createElement('button');btn.className='copy-btn code-copy-btn';btn.textContent='📋 复制';
    btn.setAttribute('data-copy-text',b.textContent||'');
    btn.style.cssText='position:absolute;top:8px;right:8px;z-index:10;';
    w.appendChild(btn);
  });
  document.querySelectorAll('.tip-box,.warning-box,.info-box').forEach(function(box){
    if(box.querySelector('.copy-btn'))return;
    var btn=document.createElement('button');btn.className='copy-btn box-copy-btn';btn.textContent='复制';
    btn.setAttribute('data-copy-text',box.textContent||'');
    btn.style.cssText='position:absolute;bottom:8px;right:8px;z-index:10;font-size:0.75rem;padding:4px 10px;min-height:36px;min-width:36px;';
    box.style.position='relative';box.appendChild(btn);
  });
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',autoCopyButtons);else autoCopyButtons();

// ========== 5. Search (Full Rewrite) ==========
var searchIndex=null;
var searchIndexLoading=false;

function loadSearchIndex(cb){
  if(searchIndex)return cb(searchIndex);
  if(searchIndexLoading)return;
  searchIndexLoading=true;
  var base=window.location.pathname.replace(/[^/]*\.html?$/,'');
  // Also try going up one level for subpages
  var paths=[base+'search-index.json'];
  if(base.indexOf('/')>-1){
    var up=base.replace(/[^/]+\/$/,'');
    paths.push(up+'search-index.json');
  }
  paths.push('search-index.json');
  (function tryPath(i){
    if(i>=paths.length){searchIndexLoading=false;cb([]);return;}
    fetch(paths[i]).then(function(r){if(!r.ok)throw new Error('404');return r.json();}).then(function(d){searchIndex=d||[];cb(searchIndex);}).catch(function(){tryPath(i+1);});
  })(0);
}

function performSearch(q){
  if(!q||q.length<1)return[];
  var terms=q.toLowerCase().trim().split(/\s+/).filter(function(t){return t.length>0;});
  if(!terms.length)return[];
  var results=[];
  (searchIndex||[]).forEach(function(item){
    var title=(item.title||'').toLowerCase();
    var desc=(item.description||'').toLowerCase();
    var content=(item.content||'').toLowerCase();
    var paragraphs=item.paragraphs||[];
    var score=0;
    var matchedParagraphs=[];

    terms.forEach(function(t){
      // Title match = highest weight
      if(title.indexOf(t)!==-1)score+=10;
      // Description match
      if(desc.indexOf(t)!==-1)score+=5;
      // Content match
      var ci=content.indexOf(t);
      if(ci!==-1)score+=2;

      // Find matching paragraphs for highlighting
      paragraphs.forEach(function(p){
        if(p.toLowerCase().indexOf(t)!==-1){
          score+=3;
          if(matchedParagraphs.indexOf(p)===-1)matchedParagraphs.push(p);
        }
      });
    });

    if(score>0){
      results.push({
        title:item.title,
        url:item.url,
        description:item.description||'',
        score:score,
        paragraphs:matchedParagraphs.slice(0,3)
      });
    }
  });
  return results.sort(function(a,b){return b.score-a.score;}).slice(0,20);
}

// In-page highlight search
function highlightOnPage(q){
  // Remove existing highlights
  document.querySelectorAll('.search-highlight').forEach(function(el){
    var parent=el.parentNode;
    parent.replaceChild(document.createTextNode(el.textContent),el);
    parent.normalize();
  });
  document.querySelectorAll('.search-highlight-paragraph').forEach(function(el){el.classList.remove('search-highlight-paragraph');});

  if(!q||q.length<1)return 0;

  var terms=q.toLowerCase().trim().split(/\s+/).filter(function(t){return t.length>0;});
  if(!terms.length)return 0;

  // Search in all visible text containers
  var containers=document.querySelectorAll('main, .container, .page-wrap, article, section, .card, .tile, .method-tile, .phase-tile, .step-tile, .warning-box, .tip-box, .info-box, p, li, td, th, h1, h2, h3, h4, h5, h6, span, strong, em, b, .desc, .meta, .text');
  var count=0;

  var walker=document.createTreeWalker(
    document.querySelector('main')||document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode:function(node){
        // Skip script/style/nav/footer
        var p=node.parentElement;
        if(!p)return NodeFilter.FILTER_REJECT;
        var tag=p.tagName.toLowerCase();
        if(tag==='script'||tag==='style'||tag==='nav'||tag==='footer'||tag==='button'||tag==='input')return NodeFilter.FILTER_REJECT;
        if(p.closest('.navbar')||p.closest('footer')||p.closest('.search-modal'))return NodeFilter.FILTER_REJECT;
        if(!node.textContent.trim())return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    }
  );

  var textNodes=[];
  while(walker.nextNode())textNodes.push(walker.currentNode);

  textNodes.forEach(function(node){
    var text=node.textContent;
    var lower=text.toLowerCase();
    var found=false;
    terms.forEach(function(t){if(lower.indexOf(t)!==-1)found=true;});
    if(!found)return;

    // Mark parent paragraph as highlighted
    var parent=node.parentElement;
    if(parent){
      var block=parent.closest('p, li, div.card, div.tile, div.method-tile, div.phase-tile, div.step-tile, div.warning-box, div.tip-box, div.info-box, section, article, td, th');
      if(block&&!block.classList.contains('search-highlight-paragraph')){
        block.classList.add('search-highlight-paragraph');
      }
    }

    // Create highlighted version
    var regex=new RegExp('('+terms.map(function(t){return t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}).join('|')+')','gi');
    var parts=text.split(regex);
    if(parts.length<=1)return; // No actual match in split

    var frag=document.createDocumentFragment();
    parts.forEach(function(part){
      if(!part)return;
      var isMatch=false;
      terms.forEach(function(t){if(part.toLowerCase()===t)isMatch=true;});
      if(isMatch){
        var mark=document.createElement('mark');
        mark.className='search-highlight';
        mark.textContent=part;
        frag.appendChild(mark);
        count++;
      }else{
        frag.appendChild(document.createTextNode(part));
      }
    });
    node.parentNode.replaceChild(frag,node);
  });

  // Scroll to first highlight
  var first=document.querySelector('.search-highlight');
  if(first)first.scrollIntoView({behavior:'smooth',block:'center'});

  return count;
}

function clearHighlights(){
  document.querySelectorAll('.search-highlight').forEach(function(el){
    var parent=el.parentNode;
    parent.replaceChild(document.createTextNode(el.textContent),el);
    parent.normalize();
  });
  document.querySelectorAll('.search-highlight-paragraph').forEach(function(el){el.classList.remove('search-highlight-paragraph');});
}

function ensureSearchModal(){
  var ex=document.getElementById('searchModal');if(ex)return ex;
  var m=document.createElement('div');m.id='searchModal';m.className='search-modal';
  m.innerHTML=
    '<div class="search-modal-content">'+
      '<div class="search-modal-header">'+
        '<input type="text" class="search-modal-input" placeholder="搜索药材、手串、车型、沉香…" autocomplete="off" aria-label="搜索">'+
        '<button class="search-modal-clear" aria-label="清空" style="display:none;background:none;border:none;font-size:1.2rem;color:var(--text-muted);cursor:pointer;padding:4px 8px;min-height:44px;min-width:44px;">✕</button>'+
        '<button class="search-modal-close" aria-label="关闭">&times;</button>'+
      '</div>'+
      '<div class="search-modal-tabs">'+
        '<button class="search-tab active" data-mode="site">全站搜索</button>'+
        '<button class="search-tab" data-mode="page">本页查找</button>'+
      '</div>'+
      '<div class="search-modal-results"></div>'+
    '</div>';
  document.body.appendChild(m);return m;
}

(function(){
  loadSearchIndex(function(){});
  var modal=ensureSearchModal();
  var input=modal.querySelector('.search-modal-input');
  var results=modal.querySelector('.search-modal-results');
  var closeBtn=modal.querySelector('.search-modal-close');
  var clearBtn=modal.querySelector('.search-modal-clear');
  var tabs=modal.querySelectorAll('.search-tab');
  var searchMode='site'; // 'site' or 'page'

  tabs.forEach(function(tab){
    tab.addEventListener('click',function(){
      tabs.forEach(function(t){t.classList.remove('active');});
      tab.classList.add('active');
      searchMode=tab.getAttribute('data-mode');
      if(input.value)handle(input.value);
    });
  });

  function open(q){
    modal.classList.add('active');
    setTimeout(function(){input.focus();if(q){input.value=q;handle(q);}},50);
  }
  function close(){
    modal.classList.remove('active');
    input.value='';
    results.innerHTML='';
    clearBtn.style.display='none';
    clearHighlights();
  }

  function handle(q){
    clearBtn.style.display=q?'block':'none';
    if(!q||q.length<1){
      results.innerHTML='<div class="search-hint">输入关键词开始搜索</div>';
      clearHighlights();
      return;
    }

    if(searchMode==='page'){
      // In-page search with highlighting
      clearHighlights();
      var count=highlightOnPage(q);
      if(count===0){
        results.innerHTML='<div class="search-no-results">未找到相关内容</div>';
      }else{
        results.innerHTML='<div class="search-page-result">在本页找到 <strong>'+count+'</strong> 处匹配</div>';
      }
      return;
    }

    // Site-wide search
    clearHighlights();
    var r=performSearch(q);
    if(r.length===0){
      results.innerHTML='<div class="search-no-results">未找到相关内容</div>';
      return;
    }
    var h='<div class="search-results-list">';
    r.forEach(function(item){
      var desc=item.description||'';
      // Show matching paragraphs if available
      var paras='';
      if(item.paragraphs&&item.paragraphs.length>0){
        paras='<div class="search-result-paras">';
        item.paragraphs.forEach(function(p){
          // Truncate and highlight matching terms
          var truncated=p.length>120?p.substring(0,120)+'…':p;
          var terms=q.toLowerCase().trim().split(/\s+/);
          var highlighted=truncated;
          terms.forEach(function(t){
            var re=new RegExp('('+t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+')','gi');
            highlighted=highlighted.replace(re,'<mark class="search-highlight">$1</mark>');
          });
          paras+='<div class="search-result-para">'+highlighted+'</div>';
        });
        paras+='</div>';
      }
      h+='<a href="'+escapeHtml(item.url)+'" class="search-result-item">'+
        '<div class="search-result-title">'+escapeHtml(item.title)+'</div>'+
        (desc?'<div class="search-result-desc">'+escapeHtml(desc)+'</div>':'')+
        paras+
      '</a>';
    });
    h+='</div>';
    results.innerHTML=h;
  }

  // Bind search buttons
  var sb=document.getElementById('searchBtn');
  if(sb)sb.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();open();});
  var hi=document.getElementById('homeSearchInput'),hb=document.getElementById('homeSearchBtn');
  if(hi&&hb){
    hb.addEventListener('click',function(){open(hi.value);});
    hi.addEventListener('keydown',function(e){if(e.key==='Enter')open(hi.value);});
  }

  // Input handling with debounce
  var dt=null;
  input.addEventListener('input',function(){
    clearTimeout(dt);
    dt=setTimeout(function(){handle(input.value);},200);
  });

  // Clear button
  clearBtn.addEventListener('click',function(){
    input.value='';
    clearBtn.style.display='none';
    results.innerHTML='<div class="search-hint">输入关键词开始搜索</div>';
    clearHighlights();
    input.focus();
  });

  // Close
  if(closeBtn)closeBtn.addEventListener('click',function(e){e.preventDefault();close();});
  modal.addEventListener('click',function(e){if(e.target===modal)close();});
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&modal.classList.contains('active'))close();
    // Ctrl/Cmd+K to open search
    if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();open();}
  });
  results.innerHTML='<div class="search-hint">输入关键词开始搜索</div>';
})();

// ========== 6. Guestbook ==========
(function(){
  var form=document.getElementById('guestbookForm');
  var list=document.getElementById('guestbookList');
  if(!form||!list)return;
  var STORAGE_KEY='guestbook_msgs';
  function loadMsgs(){try{return JSON.parse(localStorage.getItem(STORAGE_KEY))||[];}catch(e){return[];}}
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
    if(!text)return;
    var msgs=loadMsgs();
    msgs.push({name:name,text:text,time:new Date().toLocaleString('zh-CN')});
    saveMsgs(msgs);
    document.getElementById('guestName').value='';
    document.getElementById('guestMsg').value='';
    renderMsgs();
  });
  renderMsgs();
})();

// ========== 7. Fade-in on Scroll ==========
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
