// 邮箱反爬混淆：源码中绝不出现明文邮箱地址，
// 仅在运行时由 data-obf-user / data-obf-domain 拼回真实地址。
// 爬虫直接抓源码只能拿到 [email protected] 占位符；人工浏览器打开则正常显示可点的邮箱。
(function () {
  var els = document.querySelectorAll('a.obf-email');
  for (var i = 0; i < els.length; i++) {
    var el = els[i];
    var u = el.getAttribute('data-obf-user');
    var d = el.getAttribute('data-obf-domain');
    if (!u || !d) continue;
    var email = u + '@' + d;
    el.setAttribute('href', 'mailto:' + email);
    el.textContent = email;
  }
})();
