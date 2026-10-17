/*!
 * tools/audio.js — 10 音频转 WAV（工具箱·按需加载子模块）
 *
 * 由 tools.js 框架在用户点开对应卡片时才注入执行，不参与首屏加载。
 * 与主文件同一套红线：零外部依赖、零 CDN、零网络请求，文件不离开浏览器。
 * 用到的公共函数全部经顶部解构自 window.LXTools.api 取得；
 * 不要在 IIFE 之外挂任何全局，也不要依赖别的子模块。
 */
(function () {
  'use strict';
  var _ = (window.LXTools || {}).api;
  if (!_) return;
  var baseName = _.baseName, bindDrop = _.bindDrop, btnOf = _.btnOf, esc = _.esc, 
    extOf = _.extOf, fmtBytes = _.fmtBytes, fmtNum = _.fmtNum, panelOf = _.panelOf, 
    plainErr = _.plainErr, renderList = _.renderList, runSeq = _.runSeq, 
    scrollPanel = _.scrollPanel, setStat = _.setStat, sizeCell = _.sizeCell, toast = _.toast, 
    valOf = _.valOf, zipItems = _.zipItems;

  /* ======================================================================
     1c. WAV 编码器（PCM 16bit；重采样与下混交给 OfflineAudioContext）
     ====================================================================== */
  function encodeWav(channels, sampleRate) {
    var nch = channels.length;
    var frames = channels[0].length;
    var dataBytes = frames * nch * 2;
    var buf = new ArrayBuffer(44 + dataBytes);
    var v = new DataView(buf);
    var pos = 0;

    function str(s) { for (var i = 0; i < s.length; i++) v.setUint8(pos++, s.charCodeAt(i)); }
    function u32(n) { v.setUint32(pos, n, true); pos += 4; }
    function u16(n) { v.setUint16(pos, n, true); pos += 2; }

    str('RIFF'); u32(36 + dataBytes); str('WAVE');
    str('fmt '); u32(16); u16(1); u16(nch);
    u32(sampleRate); u32(sampleRate * nch * 2); u16(nch * 2); u16(16);
    str('data'); u32(dataBytes);

    for (var i = 0; i < frames; i++) {
      for (var c = 0; c < nch; c++) {
        var s = channels[c][i];
        if (s > 1) s = 1; else if (s < -1) s = -1;
        v.setInt16(pos, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        pos += 2;
      }
    }
    return new Uint8Array(buf);
  }

  function peakOf(channels) {
    var peak = 0;
    for (var c = 0; c < channels.length; c++) {
      var d = channels[c];
      for (var i = 0; i < d.length; i++) {
        var a = d[i] < 0 ? -d[i] : d[i];
        if (a > peak) peak = a;
      }
    }
    return peak;
  }

  /** 把 AudioBuffer 转成 16bit PCM 通道数组（含可选重采样 / 单声道 / 归一化） */
  function audioBufferToPcm(buf, opt) {
    var rate = opt.rate > 0 ? opt.rate : buf.sampleRate;
    var nch = opt.mono ? 1 : Math.min(2, buf.numberOfChannels);

    function pack(rendered) {
      var chans = [];
      for (var c = 0; c < rendered.numberOfChannels; c++) chans.push(rendered.getChannelData(c));
      if (opt.norm) {
        var peak = peakOf(chans);
        if (peak > 0.0001) {
          var g = 0.891 / peak;   // -1 dBFS
          for (var c2 = 0; c2 < chans.length; c2++) {
            for (var i = 0; i < chans[c2].length; i++) chans[c2][i] *= g;
          }
        }
      }
      return chans;
    }

    var needResample = (rate !== buf.sampleRate) || (opt.mono && buf.numberOfChannels > 1);
    var OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    if (!needResample || !OAC) {
      var chans = [];
      for (var c = 0; c < nch; c++) chans.push(buf.getChannelData(c));
      if (opt.norm) {
        var peak = peakOf(chans);
        if (peak > 0.0001) {
          var g = 0.891 / peak;
          for (var c3 = 0; c3 < chans.length; c3++) {
            for (var j = 0; j < chans[c3].length; j++) chans[c3][j] *= g;
          }
        }
      }
      return Promise.resolve({ channels: chans, rate: buf.sampleRate });
    }

    var frames = Math.max(1, Math.ceil(buf.duration * rate));
    var ctx = new OAC(nch, frames, rate);
    var src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(ctx.destination);
    src.start();
    return ctx.startRendering().then(function (rendered) {
      return { channels: pack(rendered), rate: rate };
    });
  }
  /* ---------------- 10 音频转 WAV ---------------- */
  function setupAudio() {
    var P = panelOf('audio');
    if (!P) return;
    var items = [];
    var box = bindDrop(P, { items: items, multiple: true, onAdd: function () { refresh(); scrollPanel(P); } });

    function refresh() {
      renderList(P, items, {
        onChange: refresh,
        meta: function (it) {
          return it.meta || (extOf(it.file.name).toUpperCase() + ' · ' + fmtBytes(it.file.size));
        }
      });
      btnOf(P, 'zip').disabled = !items.some(function (it) { return it.out; });
    }

    btnOf(P, 'run').addEventListener('click', function () {
      if (!items.length) return toast(P, '先选几个音频文件', 'err');
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return toast(P, '这个浏览器不支持音频解码，换 Chrome 或 Safari 新版本试试', 'err');

      var rate = parseInt(valOf(P, 'rate'), 10) || 0;
      var mono = !!valOf(P, 'mono');
      var norm = !!valOf(P, 'norm');
      var btn = btnOf(P, 'run');
      btn.disabled = true;
      toast(P, '正在解码，长音频要等一会儿…', 'ok');

      var ctx = new AC();
      var before = 0, after = 0, errs = 0;
      runSeq(items, function (it) {
        it.out = null;
        return it.file.arrayBuffer().then(function (ab) {
          return new Promise(function (res, rej) {
            var pr = ctx.decodeAudioData(ab, res, rej);   // 老 Safari 只认回调式签名
            if (pr && pr.then) pr.then(res, rej);
          });
        }).then(function (buf) {
          return audioBufferToPcm(buf, { rate: rate, mono: mono, norm: norm });
        }).then(function (pcm) {
          it.out = new Blob([encodeWav(pcm.channels, pcm.rate)], { type: 'audio/wav' });
          it.outName = baseName(it.file.name) + '.wav';
          it.meta = pcm.channels.length + ' 声道 · ' + pcm.rate + ' Hz · ' +
            fmtNum(pcm.channels[0].length / pcm.rate, 1) + ' 秒 · ' + fmtBytes(it.out.size);
          before += it.file.size;
          after += it.out.size;
        }).catch(function (e) {
          errs++;
          it.meta = '<span class="tl-warn">' + esc(plainErr(e, '这个文件浏览器解不开，可能不是常见音频格式，也可能文件损坏')) + '</span>';
        });
      }).then(function () {
        btn.disabled = false;
        if (ctx.close) ctx.close();
        refresh();
        setStat(P, sizeCell(before, after),
          errs ? '<b>' + errs + '</b> 个文件解码失败。浏览器能解的取决于系统解码器，' +
            'mp3、m4a(AAC)、wav 基本都能过，flac、ape 之类不一定。' :
            '转出来的就是标准 PCM WAV（16 位），老设备、老软件都能直接读。');
        toast(P, errs ? ('完成，' + errs + ' 个失败') : '转换完成，可逐个下载或一次打包', errs ? 'err' : 'ok');
      });
    });

    btnOf(P, 'zip').addEventListener('click', function () {
      zipItems(items, 'wav.zip').catch(function (e) { toast(P, plainErr(e, '打包下载没成功，重试一次或一次少选几张'), 'err'); });
    });

    btnOf(P, 'clear').addEventListener('click', function () {
      box.clear();
      items.length = 0;
      refresh();
      setStat(P, null);
    });
    refresh();
  }
  window.LXTools.define('audio', setupAudio);
})();
