/**
 * AI 聊天功能 - 通过 Cloudflare Worker 代理调用 DeepSeek
 * Worker 代码见：workspace/cloudflare-worker.js
 */

// ⚠️ 部署 Cloudflare Worker 后，把 URL 替换成你的 Worker 地址
const WORKER_URL = 'https://longxiong-chat.xxx.workers.dev';

let chatOpen = false;
let chatHistory = [
  {
    role: 'system',
    content: '你是"龙兄知识库"网站的AI助手，名字叫"龙兄AI助手"。你的风格：友好、务实、略带幽默，像一个懂生活、爱折腾的朋友。你可以回答紫砂艺术、沉香鉴别、中药材、养生茶、文玩手串、数码科技、流行文化等方面的问题。如果问题超出知识范围，坦诚说不知道，不要编造。回答简洁，控制在200字以内。'
  }
];

function toggleChat() {
  chatOpen = !chatOpen;
  document.getElementById('chatWindow').classList.toggle('open', chatOpen);
  if (chatOpen) document.getElementById('chatInput').focus();
}

async function sendMessage() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  appendMessage('user', text);
  input.value = '';
  const btn = document.getElementById('chatSend');
  btn.disabled = true;
  const loadingId = appendLoading();

  try {
    chatHistory.push({ role: 'user', content: text });
    const response = await fetch(WORKER_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: 'deepseek-chat',
        messages: chatHistory,
        max_tokens: 500,
        temperature: 0.7
      })
    });

    const data = await response.json();
    const reply = data.choices?.[0]?.message?.content || '抱歉，我暂时无法回答，请稍后再试。';
    removeLoading(loadingId);
    appendMessage('bot', reply);
    chatHistory.push({ role: 'assistant', content: reply });
  } catch (err) {
    removeLoading(loadingId);
    appendMessage('bot', '网络出错了，请检查连接后重试。');
    console.error('Chat API Error:', err);
  }
  btn.disabled = false;
}

function appendMessage(role, text) {
  const c = document.getElementById('chatMessages');
  const m = document.createElement('div');
  m.className = `chat-msg ${role}`;
  m.innerHTML = `<div class="msg-avatar">${role === 'user' ? '🧑' : '🐉'}</div><div class="msg-bubble">${escapeHtml(text)}</div>`;
  c.appendChild(m);
  c.scrollTop = c.scrollHeight;
}

function appendLoading() {
  const c = document.getElementById('chatMessages');
  const id = 'loading-' + Date.now();
  const el = document.createElement('div');
  el.className = 'chat-msg bot';
  el.id = id;
  el.innerHTML = `<div class="msg-avatar">🐉</div><div class="typing-indicator"><span></span><span></span><span></span></div>`;
  c.appendChild(el);
  c.scrollTop = c.scrollHeight;
  return id;
}

function removeLoading(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

document.getElementById('chatSend').onclick = sendMessage;
document.getElementById('chatInput').addEventListener('keydown', e => {
  if (e.key === 'Enter') sendMessage();
});

document.getElementById('chatWindow').classList.remove('open');
