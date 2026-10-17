/* join.html 顶部功能键交互：搜索、主题、分享、移动端菜单（外置化，避免 CSP 拦截内联脚本） */
(function(){
  'use strict';
  var THEME_KEY='theme';
  function getAutoTheme(){ try{ if(window.matchMedia('(prefers-color-scheme: light)').matches)return'light'; }catch(e){} return'dark'; }
  function applyTheme(t){ document.body.classList.toggle('light',t==='light'); try{localStorage.setItem(THEME_KEY,t);}catch(e){} updateThemeIcon(t); }
  function updateThemeIcon(t){ var btn=document.getElementById('themeToggle'); if(!btn)return; var sun=btn.querySelector('.icon-sun'),moon=btn.querySelector('.icon-moon'); if(sun)sun.style.display=t==='dark'?'inline':'none'; if(moon)moon.style.display=t==='dark'?'none':'inline'; }
  (function initTheme(){ var saved; try{saved=localStorage.getItem(THEME_KEY);}catch(e){} var theme=(saved==='dark'||saved==='light')?saved:getAutoTheme(); applyTheme(theme); })();
  var tt=document.getElementById('themeToggle'); if(tt)tt.addEventListener('click',function(){ var cur=document.body.classList.contains('light')?'light':'dark'; applyTheme(cur==='dark'?'light':'dark'); });
  var sb=document.getElementById('searchBtn'); if(sb)sb.addEventListener('click',function(){ var q=window.prompt('搜索龙兄知识库：'); if(q!==null&&q.trim()){ window.location.href='/search.html?q='+encodeURIComponent(q.trim()); } });
  var sh=document.getElementById('shareBtn'); if(sh)sh.addEventListener('click',function(){ var url='https://longxiong.vip/join.html', title='龙兄私房-硬核爱好避坑圈'; if(navigator.share){ navigator.share({title:title, text:title, url:url}).catch(function(){}); }else{ try{navigator.clipboard.writeText(url); alert('链接已复制，可粘贴分享');}catch(e){ alert('分享链接：'+url); } } });
  var hb=document.getElementById('hamburger'); var mn=document.getElementById('joinMobileNav'); var ov=document.getElementById('joinMobileOverlay');
  function closeMenu(){ if(hb){hb.classList.remove('active');hb.setAttribute('aria-expanded','false');} if(mn)mn.classList.remove('open'); if(ov)ov.classList.remove('open'); document.body.style.overflow=''; }
  function openMenu(){ if(hb){hb.classList.add('active');hb.setAttribute('aria-expanded','true');} if(mn)mn.classList.add('open'); if(ov)ov.classList.add('open'); document.body.style.overflow='hidden'; }
  if(hb&&mn){ hb.addEventListener('click',function(){ if(mn.classList.contains('open'))closeMenu(); else openMenu(); }); }
  if(ov)ov.addEventListener('click',closeMenu);
  mn&&mn.querySelectorAll('a').forEach(function(a){ a.addEventListener('click',closeMenu); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape')closeMenu(); });
})();
