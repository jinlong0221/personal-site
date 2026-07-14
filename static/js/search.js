/**
 * search.js - 全站搜索模块（独立文件，避免与主题代码冲突）
 * [六-1] 从 app.js 拆分出来，独立加载
 * 依赖：DOM 已ready即可，无需等待 app.js
 */

// ============================================================
// 工具函数（搜索专用，保证独立运行不依赖 app.js）
// ============================================================
function searchEscapeHtml(t){
  return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#039;');
}
function searchSanitizeInput(t){
  return t.replace(/<[^>]*>/g,'').replace(/[<>"'&]/g,function(c){
    return {'<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#039;",'&':'&amp;'}[c];
  });
}

// ============================================================
// 搜索索引加载
// ============================================================
var searchIndex=null;
var searchIndexLoading=false;

function loadSearchIndex(cb){
  if(searchIndex)return cb(searchIndex);
  if(searchIndexLoading)return;
  searchIndexLoading=true;
  var base=window.location.pathname.replace(/[^/]*\.html?$/,'');
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

// ============================================================
// 全站搜索：标题+描述+正文+段落，加权评分
// ============================================================
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
      if(title.indexOf(t)!==-1)score+=10;
      if(desc.indexOf(t)!==-1)score+=5;
      if(content.indexOf(t)!==-1)score+=2;
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

// ============================================================
// 本页高亮：h1-h6/p/li/td/th 等全部文本节点
// ============================================================
function highlightOnPage(q){
  // 清除旧高亮
  document.querySelectorAll('.search-highlight').forEach(function(el){
    var parent=el.parentNode;
    parent.replaceChild(document.createTextNode(el.textContent),el);
    parent.normalize();
  });
  document.querySelectorAll('.search-highlight-paragraph').forEach(function(el){
    el.classList.remove('search-highlight-paragraph');
  });

  if(!q||q.length<1)return 0;
  var safeQ=searchSanitizeInput(q);
  var terms=safeQ.toLowerCase().trim().split(/\s+/).filter(function(t){return t.length>0;});
  if(!terms.length)return 0;

  var count=0;
  var walker=document.createTreeWalker(
    document.querySelector('main')||document.body,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode:function(node){
        var p=node.parentElement;
        if(!p)return NodeFilter.FILTER_REJECT;
        var tag=p.tagName.toLowerCase();
        if(tag==='script'||tag==='style'||tag==='nav'||tag==='footer'||tag==='button'||tag==='input'||tag==='textarea')return NodeFilter.FILTER_REJECT;
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

    var parent=node.parentElement;
    if(parent){
      var block=parent.closest('p, li, div.card, div.tile, div.method-tile, div.phase-tile, div.step-tile, div.warning-box, div.tip-box, div.info-box, section, article, td, th, h1, h2, h3, h4, h5, h6');
      if(block&&!block.classList.contains('search-highlight-paragraph')){
        block.classList.add('search-highlight-paragraph');
      }
    }

    var regex=new RegExp('('+terms.map(function(t){return t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');}).join('|')+')','gi');
    var parts=text.split(regex);
    if(parts.length<=1)return;

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
  document.querySelectorAll('.search-highlight-paragraph').forEach(function(el){
    el.classList.remove('search-highlight-paragraph');
  });
}

// ============================================================
// 搜索弹窗 UI
// ============================================================
function ensureSearchModal(){
  var ex=document.getElementById('searchModal');if(ex)return ex;
  var m=document.createElement('div');m.id='searchModal';m.className='search-modal'; m.setAttribute('role','dialog'); m.setAttribute('aria-label','搜索');
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

// ============================================================
// 搜索初始化（自动执行）
// ============================================================
(function initSearch(){
  loadSearchIndex(function(){});
  var modal=ensureSearchModal();
  var input=modal.querySelector('.search-modal-input');
  var results=modal.querySelector('.search-modal-results');
  var closeBtn=modal.querySelector('.search-modal-close');
  var clearBtn=modal.querySelector('.search-modal-clear');
  var tabs=modal.querySelectorAll('.search-tab');
  var searchMode='site';
  var pagefindReady=false;
  var pagefindSearch=null;

  // 初始化 Pagefind（全站搜索）
  if(typeof pagefind!=='undefined'){
    pagefind.search('').then(function(){pagefindReady=true;}).catch(function(){pagefindReady=false;});
  }

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
    setTimeout(function(){
      // 按需加载 pagefind.js（仅搜索页自带，全站其他页动态加载）
      if(typeof pagefind==='undefined'){
        var s=document.createElement('script');
        s.src='/pagefind/pagefind.js';
        s.onload=function(){pagefindReady=true;input.focus();if(q){input.value=q;handle(q);}};
        s.onerror=function(){input.focus();if(q){input.value=q;handle(q);}};
        document.head.appendChild(s);
      }else{
        pagefindReady=true;
        input.focus();
        if(q){input.value=q;handle(q);}
      }
    },50);
  }
  function close(){
    modal.classList.remove('active');
    input.value='';
    results.innerHTML='';
    clearBtn.style.display='none';
    clearHighlights();
  }

  function displayResults(r,q){
    if(r.length===0){
      results.innerHTML='<div class="search-no-results">暂无相关内容</div>';
      return;
    }
    var h='<div class="search-results-list">';
    r.forEach(function(item){
      var desc=item.description||item.excerpt||'';
      var paras='';
      if(item.paragraphs&&item.paragraphs.length>0){
        paras='<div class="search-result-paras">';
        item.paragraphs.forEach(function(p){
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
      h+='<a href="'+searchEscapeHtml(item.url)+'" class="search-result-item">'+
        '<div class="search-result-title">'+searchEscapeHtml(item.title)+'</div>'+
        (desc?'<div class="search-result-desc">'+searchEscapeHtml(desc)+'</div>':'')+
        paras+
      '</a>';
    });
    h+='</div>';
    results.innerHTML=h;
  }

  async function handle(q){
    q=searchSanitizeInput(q);
    clearBtn.style.display=q?'block':'none';
    if(!q||q.length<1){
      results.innerHTML='<div class="search-hint">输入关键词开始搜索</div>';
      clearHighlights();
      return;
    }
    if(searchMode==='page'){
      clearHighlights();
      var count=highlightOnPage(q);
      if(count===0){
        results.innerHTML='<div class="search-no-results">暂无相关内容</div>';
      }else{
        results.innerHTML='<div class="search-page-result">在本页找到 <strong>'+count+'</strong> 处匹配</div>';
      }
      return;
    }
    clearHighlights();
    results.innerHTML='<div class="search-hint">搜索中…</div>';

    // 优先用 Pagefind，否则降级到 search-index.json
    if(pagefindReady){
      try{
        var pf=await pagefind.search(q);
        var items=[];
        for(var i=0;i<pf.results.length&&i<20;i++){
          var d=await pf.results[i].data();
          items.push({title:d.meta&&d.meta.title||'',url:d.url,description:d.excerpt||'',paragraphs:[]});
        }
        displayResults(items,q);
        return;
      }catch(e){}
    }
    // 降级方案
    var r=performSearch(q);
    displayResults(r,q);
  }

  // 导航栏搜索按钮
  var sb=document.getElementById('searchBtn');
  if(sb)sb.addEventListener('click',function(e){e.preventDefault();e.stopPropagation();open();});

  // 首页搜索框
  var hi=document.getElementById('homeSearchInput'),hb2=document.getElementById('homeSearchBtn');
  if(hi&&hb2){
    hb2.addEventListener('click',function(){open(hi.value);});
    hi.addEventListener('keydown',function(e){if(e.key==='Enter')open(hi.value);});
  }

  // 首页搜索框清空按钮
  var homeClear=document.getElementById('homeSearchClear');
  if(hi&&homeClear){
    hi.addEventListener('input',function(){
      homeClear.style.display=hi.value?'block':'none';
    });
    homeClear.addEventListener('click',function(){
      hi.value='';
      homeClear.style.display='none';
      hi.focus();
    });
  }

  // 弹窗输入框防抖
  var dt=null;
  input.addEventListener('input',function(){
    clearTimeout(dt);
    dt=setTimeout(function(){handle(input.value);},200);
  });

  // 弹窗清空按钮
  clearBtn.addEventListener('click',function(){
    input.value='';
    clearBtn.style.display='none';
    results.innerHTML='<div class="search-hint">输入关键词开始搜索</div>';
    clearHighlights();
    input.focus();
  });

  // 关闭
  if(closeBtn)closeBtn.addEventListener('click',function(e){e.preventDefault();close();});
  modal.addEventListener('click',function(e){if(e.target===modal)close();});
  document.addEventListener('keydown',function(e){
    if(e.key==='Escape'&&modal.classList.contains('active'))close();
    if((e.ctrlKey||e.metaKey)&&e.key==='k'){e.preventDefault();open();}
  });
  results.innerHTML='<div class="search-hint">输入关键词开始搜索</div>';
})();

