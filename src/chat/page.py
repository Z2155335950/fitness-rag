CHAT_PAGE = """
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#090d0c">
  <meta name="color-scheme" content="dark">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <title>网红训练法</title>
  <link rel="preload" href="/static/fonts/LXGWWenKai-Title.woff2"
    as="font" type="font/woff2" crossorigin>
  <link rel="preload" href="/static/fonts/GlowSansSC-Body-Regular.woff2"
    as="font" type="font/woff2" crossorigin>
  <style>
    @font-face {
      font-family:"LXGW WenKai Title";
      src:url("/static/fonts/LXGWWenKai-Title.woff2") format("woff2");
      font-style:normal;
      font-weight:400 600;
      font-display:swap;
    }
    @font-face {
      font-family:"Glow Sans Body";
      src:url("/static/fonts/GlowSansSC-Body-Regular.woff2") format("woff2");
      font-style:normal;
      font-weight:400;
      font-display:swap;
    }
    @font-face {
      font-family:"Glow Sans Body";
      src:url("/static/fonts/GlowSansSC-Body-Bold.woff2") format("woff2");
      font-style:normal;
      font-weight:600 900;
      font-display:swap;
    }
    :root {
      --bg:#090d0c;
      --panel:#111715;
      --panel-soft:#161d1a;
      --line:rgba(228,219,201,.12);
      --line-strong:rgba(228,219,201,.2);
      --text:#f2eee5;
      --muted:#8d978f;
      --accent:#c8aa70;
      --accent-soft:rgba(200,170,112,.12);
      --shadow:0 28px 90px rgba(0,0,0,.38);
      --app-height:100dvh;
      --font-heading:"LXGW WenKai Title","霞鹜文楷","STKaiti",serif;
      --font-body:"Glow Sans Body","未来荧黑","PingFang SC","Microsoft YaHei",sans-serif;
    }
    * { box-sizing:border-box; }
    html,body { height:100%; }
    html { -webkit-text-size-adjust:100%; }
    body {
      margin:0;
      overflow:hidden;
      overscroll-behavior:none;
      color:var(--text);
      background:
        radial-gradient(circle at 12% -10%,rgba(45,95,72,.24),transparent 34%),
        radial-gradient(circle at 92% 18%,rgba(200,170,112,.07),transparent 26%),
        linear-gradient(145deg,#090d0c,#0c1110 55%,#080b0a);
      font:15px/1.72 var(--font-body);
    }
    button,input,textarea {
      -webkit-tap-highlight-color:transparent;
      touch-action:manipulation;
    }
    body::before {
      content:"";
      position:fixed;
      inset:0;
      pointer-events:none;
      opacity:.18;
      background-image:linear-gradient(rgba(255,255,255,.025) 1px,transparent 1px),
                       linear-gradient(90deg,rgba(255,255,255,.025) 1px,transparent 1px);
      background-size:48px 48px;
      mask-image:linear-gradient(to bottom,black,transparent 82%);
    }
    .workspace {
      position:relative;
      height:var(--app-height);
      display:grid;
      grid-template-columns:270px minmax(0,1fr);
      overflow:hidden;
    }
    .sidebar {
      position:relative;
      z-index:20;
      display:grid;
      grid-template-rows:auto auto auto 1fr auto;
      min-height:0;
      padding:20px 16px 18px;
      border-right:1px solid var(--line);
      background:rgba(8,12,11,.86);
      backdrop-filter:blur(22px);
    }
    .sidebar-backdrop { display:none; }
    .sidebar-brand {
      padding:4px 7px 18px;
      border-bottom:1px solid var(--line);
    }
    .sidebar-close {
      display:none;
      width:40px;
      height:40px;
      border:1px solid var(--line);
      border-radius:50%;
      place-items:center;
      color:var(--muted);
      background:rgba(255,255,255,.025);
      cursor:pointer;
    }
    .sidebar-brand .eyebrow { margin-bottom:8px; }
    .sidebar-brand h2 {
      margin:0;
      font-family:var(--font-heading);
      font-size:1.12rem;
      font-weight:500;
      letter-spacing:.05em;
    }
    .new-conversation {
      width:100%;
      margin:16px 0 10px;
      padding:11px 14px;
      border:1px solid rgba(200,170,112,.35);
      border-radius:10px;
      color:#e8d9ba;
      background:var(--accent-soft);
      font:500 .8rem var(--font-body);
      text-align:left;
      cursor:pointer;
    }
    .new-conversation span { float:right; color:var(--accent); font-size:1rem; }
    .history-search {
      width:100%;
      margin:2px 0 12px;
      padding:9px 11px;
      border:1px solid var(--line);
      border-radius:8px;
      outline:0;
      color:var(--text);
      background:rgba(255,255,255,.025);
      font:inherit;
      font-size:.76rem;
    }
    .history-search:focus { border-color:rgba(200,170,112,.35); }
    .conversation-list {
      min-height:0;
      overflow-y:auto;
      padding:2px 2px 12px;
      scrollbar-width:thin;
      scrollbar-color:#303a35 transparent;
    }
    .conversation-item {
      position:relative;
      display:flex;
      align-items:stretch;
      border-radius:9px;
      margin:3px 0;
      transition:background .2s ease;
    }
    .conversation-item:hover,
    .conversation-item.active { background:rgba(255,255,255,.04); }
    .conversation-main {
      min-width:0;
      flex:1;
      border:0;
      padding:10px 67px 10px 10px;
      color:inherit;
      background:transparent;
      text-align:left;
      cursor:pointer;
    }
    .conversation-title {
      display:block;
      overflow:hidden;
      color:#ded8cd;
      font-size:.79rem;
      line-height:1.45;
      text-overflow:ellipsis;
      white-space:nowrap;
    }
    .conversation-preview {
      display:block;
      overflow:hidden;
      margin-top:3px;
      color:#66716b;
      font-size:.66rem;
      line-height:1.4;
      text-overflow:ellipsis;
      white-space:nowrap;
    }
    .conversation-time {
      display:block;
      margin-top:5px;
      color:#4f5a54;
      font-size:.59rem;
      letter-spacing:.04em;
    }
    .conversation-actions {
      position:absolute;
      right:7px;
      top:9px;
      display:none;
      gap:3px;
    }
    .conversation-item:hover .conversation-actions { display:flex; }
    .conversation-actions button {
      width:25px;
      height:25px;
      border:1px solid var(--line);
      border-radius:6px;
      color:#8d978f;
      background:#111715;
      font:inherit;
      font-size:.62rem;
      cursor:pointer;
    }
    .conversation-actions button:hover { color:var(--accent); }
    .history-empty {
      padding:25px 10px;
      color:#5e6862;
      text-align:center;
      font-size:.72rem;
      line-height:1.7;
    }
    .sidebar-foot {
      padding:13px 8px 0;
      border-top:1px solid var(--line);
      color:#4f5953;
      font-size:.61rem;
      letter-spacing:.08em;
    }
    .sidebar-foot {
      display:grid;
      gap:9px;
    }
    .view-switch-title {
      margin-bottom:7px;
      color:#68736c;
      font-size:.62rem;
      letter-spacing:.12em;
    }
    .view-switch-options {
      display:grid;
      grid-template-columns:1fr 1fr;
      gap:3px;
      padding:3px;
      border:1px solid var(--line);
      border-radius:9px;
      background:rgba(255,255,255,.025);
    }
    .view-switch-option {
      min-height:30px;
      border:0;
      border-radius:6px;
      color:#78837c;
      background:transparent;
      font:inherit;
      font-size:.68rem;
      letter-spacing:.06em;
      cursor:pointer;
    }
    .view-switch-option:hover { color:#d8cebd; }
    .view-switch-option[aria-pressed="true"] {
      color:#17120a;
      background:var(--accent);
    }
    .archive-label {
      color:#4f5953;
      letter-spacing:.08em;
    }
    .shell {
      position:relative;
      width:min(980px,calc(100% - 28px));
      height:var(--app-height);
      min-width:0;
      min-height:0;
      margin:0 auto;
      display:grid;
      grid-template-rows:auto 1fr auto;
    }
    header {
      display:flex;
      align-items:center;
      justify-content:space-between;
      padding:26px 6px 20px;
      border-bottom:1px solid var(--line);
    }
    .brand { display:flex; align-items:center; gap:15px; }
    .mark {
      width:46px;
      height:46px;
      border:1px solid rgba(200,170,112,.45);
      border-radius:50%;
      display:grid;
      place-items:center;
      color:var(--accent);
      font-family:var(--font-heading);
      font-size:18px;
      box-shadow:inset 0 0 0 5px rgba(200,170,112,.035);
    }
    .eyebrow {
      color:var(--accent);
      font-size:.65rem;
      letter-spacing:.24em;
      line-height:1;
      margin-bottom:7px;
      text-transform:uppercase;
    }
    h1 {
      margin:0;
      font-family:var(--font-heading);
      font-size:1.5rem;
      font-weight:500;
      line-height:1;
      letter-spacing:.04em;
    }
    .header-actions { display:flex; align-items:center; gap:18px; }
    .status {
      display:flex;
      align-items:center;
      gap:8px;
      color:var(--muted);
      font-size:.66rem;
      letter-spacing:.12em;
      text-transform:uppercase;
    }
    .status-dot {
      width:6px;
      height:6px;
      border-radius:50%;
      background:var(--accent);
      box-shadow:0 0 0 4px var(--accent-soft);
    }
    .new-chat {
      display:inline-flex;
      align-items:center;
      justify-content:center;
      border:0;
      background:transparent;
      color:#c4bbb0;
      padding:8px 0;
      font:inherit;
      font-size:.78rem;
      cursor:pointer;
      transition:color .2s ease;
    }
    .new-chat:hover { color:var(--accent); }
    .mobile-icon { display:none; }
    .view-toggle {
      display:inline-flex;
      align-items:center;
      justify-content:center;
      gap:7px;
      min-height:36px;
      padding:0 11px;
      border:1px solid var(--line);
      border-radius:10px;
      color:#aaa398;
      background:rgba(255,255,255,.02);
      font:inherit;
      font-size:.72rem;
      cursor:pointer;
      transition:border-color .2s ease,color .2s ease,background .2s ease;
    }
    .view-toggle:hover {
      color:var(--accent);
      border-color:rgba(200,170,112,.32);
      background:var(--accent-soft);
    }
    .view-icon {
      display:none;
      place-items:center;
    }
    :root[data-view="mobile"] .view-icon-desktop { display:grid; }
    :root:not([data-view="mobile"]) .view-icon-mobile { display:grid; }
    .view-toggle-label { white-space:nowrap; }
    .mobile-history {
      display:none;
      border:0;
      color:#aaa398;
      background:transparent;
      font:inherit;
      font-size:1.05rem;
      cursor:pointer;
    }
    #messages {
      position:relative;
      overflow-y:auto;
      min-height:0;
      overscroll-behavior:contain;
      -webkit-overflow-scrolling:touch;
      scrollbar-width:thin;
      scrollbar-color:#303a35 transparent;
      padding:32px 6px 26px;
    }
    .empty {
      min-height:100%;
      display:flex;
      flex-direction:column;
      align-items:center;
      justify-content:center;
      text-align:center;
      padding-bottom:7vh;
      animation:fade .6s ease both;
    }
    .empty-ring {
      width:78px;
      height:78px;
      border:1px solid rgba(200,170,112,.26);
      border-radius:50%;
      display:grid;
      place-items:center;
      margin-bottom:22px;
      color:var(--accent);
      font-family:var(--font-heading);
      font-size:1.6rem;
    }
    .empty h2 {
      margin:0 0 8px;
      font-family:var(--font-heading);
      font-size:clamp(1.3rem,2.6vw,1.8rem);
      font-weight:400;
      letter-spacing:.05em;
    }
    .empty p {
      margin:0;
      color:var(--muted);
      font-size:.82rem;
      letter-spacing:.08em;
    }
    .suggestions { display:none; }
    .message {
      display:flex;
      align-items:flex-start;
      gap:12px;
      margin:0 0 22px;
      animation:rise .32s ease both;
    }
    .message.user { flex-direction:row-reverse; }
    .avatar {
      width:30px;
      height:30px;
      flex:none;
      border-radius:50%;
      display:grid;
      place-items:center;
      color:var(--accent);
      border:1px solid var(--line-strong);
      background:#101513;
      font-family:var(--font-heading);
      font-size:.75rem;
    }
    .user .avatar {
      color:#17120a;
      background:var(--accent);
      border-color:var(--accent);
      font-family:inherit;
      font-weight:700;
    }
    .bubble {
      max-width:min(78%,720px);
      padding:16px 19px;
      border:1px solid var(--line);
      border-radius:4px 18px 18px 18px;
      background:linear-gradient(145deg,rgba(24,32,29,.94),rgba(16,22,20,.94));
      box-shadow:var(--shadow);
      white-space:pre-wrap;
      overflow-wrap:anywhere;
    }
    .user .bubble {
      color:#18140c;
      border-color:rgba(200,170,112,.55);
      border-radius:18px 4px 18px 18px;
      background:linear-gradient(135deg,#d4ba86,#be9d61);
      box-shadow:0 16px 45px rgba(0,0,0,.2);
    }
    .bubble p { margin:0 0 .8em; }
    .bubble p:last-child { margin-bottom:0; }
    .bubble h1,.bubble h2,.bubble h3,.bubble h4 {
      margin:.2em 0 .65em;
      color:inherit;
      font-family:var(--font-heading);
      font-weight:500;
      line-height:1.35;
    }
    .bubble h1 { font-size:1.2rem; }
    .bubble h2 { font-size:1.08rem; }
    .bubble h3,.bubble h4 { font-size:.95rem; }
    .bubble ul,.bubble ol {
      margin:.25em 0 .9em;
      padding-left:1.35em;
    }
    .bubble li { margin:.28em 0; }
    .bubble strong { font-weight:700; }
    .assistant .bubble h1,.assistant .bubble h2,
    .assistant .bubble h3,.assistant .bubble h4 { color:#e3d0aa; }
    .assistant .bubble strong { color:#eee1c6; }
    .bubble code {
      padding:.1em .35em;
      border-radius:4px;
      background:rgba(255,255,255,.07);
      color:#ead6ad;
    }
    .bubble blockquote {
      margin:.8em 0;
      padding:.45em .8em;
      border-left:2px solid var(--accent);
      color:#b9c2bb;
      background:rgba(255,255,255,.025);
    }
    .bubble a { color:var(--accent); }
    .evidence {
      display:flex;
      flex-wrap:wrap;
      gap:6px;
      margin-top:14px;
      padding-top:11px;
      border-top:1px solid var(--line);
      white-space:normal;
    }
    .tag {
      color:#a9b3ac;
      background:rgba(255,255,255,.035);
      border:1px solid rgba(255,255,255,.055);
      border-radius:2px;
      padding:2px 7px;
      font-size:.66rem;
      letter-spacing:.04em;
      text-decoration:none;
    }
    a.tag:hover { border-color:rgba(200,170,112,.45); }
    .feedback {
      display:flex;
      flex-wrap:wrap;
      align-items:center;
      gap:6px;
      margin-top:10px;
      padding-top:9px;
      border-top:1px solid rgba(255,255,255,.055);
    }
    .feedback button {
      border:1px solid rgba(255,255,255,.075);
      border-radius:6px;
      padding:4px 8px;
      color:#7f8a83;
      background:rgba(255,255,255,.025);
      font:inherit;
      font-size:.66rem;
      cursor:pointer;
    }
    .feedback button:hover {
      color:var(--accent);
      border-color:rgba(200,170,112,.3);
    }
    .feedback button.selected {
      color:#16120a;
      border-color:var(--accent);
      background:var(--accent);
    }
    .feedback-state {
      color:#68736c;
      font-size:.62rem;
    }
    .feedback-more {
      flex-basis:100%;
      display:flex;
      flex-wrap:wrap;
      gap:5px;
      padding-top:4px;
    }
    .feedback-more[hidden] { display:none; }
    .feedback-comment {
      flex-basis:100%;
      display:flex;
      gap:6px;
      margin-top:3px;
    }
    .feedback-comment input {
      flex:1;
      min-width:0;
      border:1px solid var(--line);
      border-radius:6px;
      padding:6px 8px;
      color:var(--text);
      background:rgba(0,0,0,.15);
      font:inherit;
      font-size:.66rem;
      outline:0;
    }
    .composer { padding:8px 0 22px; }
    .composer-box {
      display:flex;
      align-items:flex-end;
      gap:12px;
      min-height:66px;
      padding:12px 13px 12px 20px;
      border:1px solid var(--line-strong);
      border-radius:18px;
      background:rgba(17,23,21,.88);
      backdrop-filter:blur(18px);
      box-shadow:0 24px 70px rgba(0,0,0,.3);
      transition:border-color .2s ease,box-shadow .2s ease;
    }
    .composer-box:focus-within {
      border-color:rgba(200,170,112,.42);
      box-shadow:0 24px 70px rgba(0,0,0,.34),0 0 0 3px rgba(200,170,112,.035);
    }
    textarea {
      flex:1;
      resize:none;
      min-height:32px;
      max-height:150px;
      border:0;
      outline:0;
      padding:5px 0;
      color:var(--text);
      background:transparent;
      font:inherit;
      line-height:1.65;
    }
    textarea::placeholder { color:#68726c; }
    .send {
      width:42px;
      height:42px;
      flex:none;
      border:1px solid rgba(200,170,112,.45);
      border-radius:50%;
      color:var(--accent);
      background:rgba(200,170,112,.075);
      font-size:1.15rem;
      cursor:pointer;
      transition:transform .2s ease,background .2s ease,color .2s ease;
    }
    .send:hover {
      color:#17120a;
      background:var(--accent);
      transform:translateY(-1px);
    }
    .send:disabled { opacity:.42; cursor:wait; transform:none; }
    .footnote {
      margin-top:9px;
      color:#59635d;
      text-align:center;
      font-size:.64rem;
      letter-spacing:.1em;
    }
    .typing { display:inline-flex; gap:5px; padding:3px 0; }
    .typing i {
      width:5px;
      height:5px;
      border-radius:50%;
      background:var(--accent);
      animation:pulse 1.1s infinite ease-in-out;
    }
    .typing i:nth-child(2) { animation-delay:.14s; }
    .typing i:nth-child(3) { animation-delay:.28s; }
    @keyframes pulse {
      0%,100% { opacity:.2; transform:translateY(0); }
      50% { opacity:1; transform:translateY(-3px); }
    }
    @keyframes rise {
      from { opacity:0; transform:translateY(8px); }
      to { opacity:1; transform:translateY(0); }
    }
    @keyframes fade { from { opacity:0; } to { opacity:1; } }
  </style>
  <style id="mobileViewStyles" media="(max-width:760px)">
      body { font-size:16px; }
      body::before {
        opacity:.12;
        background-size:32px 32px;
      }
      .workspace {
        display:block;
        height:var(--app-height);
        overflow:hidden;
      }
      .sidebar {
        position:fixed;
        inset:
          0
          auto
          0
          max(0px, calc((100vw - 430px) / 2));
        z-index:40;
        width:min(90vw,360px);
        overflow:hidden;
        padding:
          calc(env(safe-area-inset-top) + 14px)
          16px
          calc(env(safe-area-inset-bottom) + 14px);
        transform:translateX(-104%);
        transition:transform .24s cubic-bezier(.22,.8,.28,1);
        isolation:isolate;
        border-right-color:var(--line-strong);
        background:#080d0b;
        backdrop-filter:none;
        box-shadow:24px 0 70px rgba(0,0,0,.52);
      }
      .sidebar.open { transform:translateX(0); }
      .sidebar-brand {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:12px;
        min-height:54px;
        padding:0 0 14px;
      }
      .sidebar-brand > div {
        min-width:0;
        padding-right:8px;
      }
      .sidebar-brand .eyebrow {
        display:block;
        margin-bottom:5px;
      }
      .sidebar-brand h2 {
        overflow:hidden;
        font-size:1.05rem;
        text-overflow:ellipsis;
        white-space:nowrap;
      }
      .sidebar-close {
        display:grid;
        flex:none;
      }
      .new-conversation {
        min-height:48px;
        margin:14px 0 10px;
        font-size:.86rem;
      }
      .history-search {
        min-height:44px;
        margin-bottom:10px;
        padding:10px 12px;
        font-size:.86rem;
      }
      .conversation-main {
        min-height:64px;
        padding:10px 88px 10px 11px;
      }
      .conversation-title { font-size:.86rem; }
      .conversation-preview { font-size:.73rem; }
      .conversation-time { font-size:.65rem; }
      .conversation-actions {
        display:flex;
        right:8px;
        top:14px;
        gap:4px;
      }
      .conversation-actions button {
        width:34px;
        height:34px;
        font-size:.7rem;
      }
      .sidebar-foot { padding:12px 4px 0; }
      .view-switch-option {
        min-height:38px;
        font-size:.76rem;
      }
      .sidebar-backdrop {
        display:none;
        position:fixed;
        inset:0;
        z-index:35;
        background:rgba(0,0,0,.72);
        backdrop-filter:blur(4px);
      }
      .sidebar-backdrop.open { display:block; }
      .shell {
        width:100%;
        height:var(--app-height);
        grid-template-rows:auto minmax(0,1fr) auto;
      }
      header {
        display:grid;
        grid-template-columns:minmax(0,1fr) auto;
        gap:8px;
        min-height:calc(60px + env(safe-area-inset-top));
        padding:
          calc(env(safe-area-inset-top) + 10px)
          14px
          10px;
        background:rgba(9,13,12,.82);
        backdrop-filter:blur(18px);
      }
      .brand {
        gap:10px;
        min-width:0;
      }
      .brand > div {
        min-width:0;
      }
      .mark {
        width:36px;
        height:36px;
        font-size:15px;
        box-shadow:inset 0 0 0 4px rgba(200,170,112,.035);
      }
      .eyebrow { display:none; }
      h1 {
        overflow:hidden;
        max-width:100%;
        font-size:1.08rem;
        line-height:1.2;
        text-overflow:ellipsis;
        white-space:nowrap;
      }
      .header-actions {
        flex:none;
        gap:2px;
      }
      .header-actions .status { display:none; }
      .view-toggle {
        width:auto;
        min-width:66px;
        height:42px;
        min-height:42px;
        padding:0 9px;
        border:1px solid var(--line);
        border-radius:10px;
        background:rgba(255,255,255,.025);
      }
      .view-toggle .view-toggle-label {
        display:inline;
        font-size:.68rem;
      }
      .mobile-history,
      .new-chat {
        display:grid;
        width:42px;
        height:42px;
        padding:0;
        place-items:center;
        border:0;
        border-radius:50%;
        color:#c6beb2;
        background:transparent;
      }
      .mobile-history { display:grid; }
      .new-chat {
        font-size:0;
        transition:background .2s ease,color .2s ease;
      }
      .new-chat .desktop-label { display:none; }
      .new-chat .mobile-icon { display:grid; place-items:center; }
      .new-chat:active,
      .mobile-history:active { background:rgba(200,170,112,.1); }
      #messages {
        padding:18px 14px 20px;
        min-height:0;
        scroll-padding-bottom:16px;
      }
      .empty {
        justify-content:flex-start;
        padding:10vh 4px 24px;
      }
      .empty-ring {
        width:68px;
        height:68px;
        margin-bottom:18px;
        font-size:1.4rem;
      }
      .empty h2 {
        margin-bottom:7px;
        font-size:1.42rem;
      }
      .empty p {
        max-width:260px;
        font-size:.84rem;
        line-height:1.65;
        letter-spacing:.02em;
      }
      .suggestions {
        display:grid;
        width:100%;
        max-width:370px;
        gap:8px;
        margin-top:26px;
      }
      .prompt-chip {
        min-height:46px;
        padding:10px 14px;
        border:1px solid var(--line);
        border-radius:14px;
        color:#c8c1b6;
        background:rgba(255,255,255,.025);
        font:inherit;
        font-size:.83rem;
        line-height:1.45;
        text-align:left;
      }
      .prompt-chip::after {
        content:"›";
        float:right;
        margin-left:12px;
        color:var(--accent);
        font-size:1.15rem;
        line-height:1.2;
      }
      .prompt-chip:active {
        border-color:rgba(200,170,112,.35);
        background:var(--accent-soft);
      }
      .message {
        gap:8px;
        margin-bottom:18px;
      }
      .avatar {
        width:28px;
        height:28px;
        font-size:.68rem;
      }
      .bubble {
        max-width:calc(100% - 36px);
        padding:12px 14px;
        border-radius:4px 16px 16px 16px;
        font-size:.94rem;
        line-height:1.68;
        box-shadow:0 12px 34px rgba(0,0,0,.18);
      }
      .user .bubble {
        max-width:86%;
        border-radius:16px 4px 16px 16px;
      }
      .evidence {
        gap:5px;
        margin-top:11px;
        padding-top:9px;
      }
      .tag {
        padding:3px 7px;
        font-size:.66rem;
      }
      .feedback {
        gap:7px;
        margin-top:9px;
        padding-top:9px;
      }
      .feedback button {
        min-height:34px;
        padding:6px 10px;
        font-size:.72rem;
      }
      .feedback-state { font-size:.68rem; }
      .feedback-comment {
        flex-direction:column;
      }
      .feedback-comment input {
        min-height:40px;
        padding:8px 10px;
        font-size:16px;
      }
      .composer {
        padding:
          7px
          12px
          calc(env(safe-area-inset-bottom) + 9px);
        background:linear-gradient(to top,rgba(8,12,11,.98) 65%,rgba(8,12,11,0));
      }
      .composer-box {
        min-height:56px;
        gap:8px;
        padding:8px 8px 8px 15px;
        border-radius:22px;
        background:rgba(20,27,24,.96);
        box-shadow:0 16px 42px rgba(0,0,0,.3);
      }
      textarea {
        min-height:38px;
        max-height:120px;
        padding:7px 0;
        font-size:16px;
        line-height:1.55;
      }
      .send {
        width:42px;
        height:42px;
        font-size:1.12rem;
      }
      .send:active {
        color:#17120a;
        background:var(--accent);
        transform:scale(.96);
      }
      .footnote {
        margin-top:5px;
        padding-bottom:1px;
        font-size:.62rem;
        letter-spacing:.05em;
      }
    @media (max-width:350px) {
      h1 { font-size:1rem; }
      .status { display:none; }
      .view-toggle {
        width:42px;
        min-width:42px;
        padding:0;
        border:0;
        border-radius:50%;
        background:transparent;
      }
      .view-toggle .view-toggle-label { display:none; }
      #messages { padding-inline:11px; }
      .composer { padding-inline:9px; }
    }
  </style>
  <style>
    @media (min-width:761px) {
      :root[data-view="mobile"] .workspace {
        width:min(430px,100%);
        margin:0 auto;
        border-inline:1px solid var(--line);
        box-shadow:0 0 80px rgba(0,0,0,.45);
      }
    }
    @media (max-width:760px) {
      :root[data-view="desktop"] body {
        overflow:auto;
        overscroll-behavior:auto;
      }
      :root[data-view="desktop"] .workspace {
        width:980px;
        min-width:980px;
      }
      :root[data-view="desktop"] .view-toggle-label { display:none; }
    }
    @media (prefers-reduced-motion:reduce) {
      *,*::before,*::after {
        scroll-behavior:auto !important;
        animation-duration:.01ms !important;
        animation-iteration-count:1 !important;
        transition-duration:.01ms !important;
      }
    }
  </style>
</head>
<body>
<div class="workspace">
  <aside id="sidebar" class="sidebar" aria-label="历史对话">
    <div class="sidebar-brand">
      <div>
        <div class="eyebrow">Archive</div>
        <h2>历史对话</h2>
      </div>
      <button id="sidebarClose" class="sidebar-close" type="button"
        aria-label="关闭历史记录">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <path d="M6 6l12 12M18 6L6 18"></path>
        </svg>
      </button>
    </div>
    <button id="newConversation" class="new-conversation" type="button">
      开始新对话 <span>＋</span>
    </button>
    <input id="conversationSearch" class="history-search"
      autocomplete="off" placeholder="搜索历史">
    <div id="conversationList" class="conversation-list"></div>
    <div class="sidebar-foot">
      <div>
        <div class="view-switch-title">页面版本</div>
        <div class="view-switch-options" role="group" aria-label="页面版本">
          <button class="view-switch-option" type="button"
            data-view-choice="desktop" aria-pressed="false">网页版</button>
          <button class="view-switch-option" type="button"
            data-view-choice="mobile" aria-pressed="false">手机版</button>
        </div>
      </div>
      <span class="archive-label">LOCAL ARCHIVE · SQLITE</span>
    </div>
  </aside>
  <div id="sidebarBackdrop" class="sidebar-backdrop"></div>
  <div class="shell">
    <header>
      <div class="brand">
        <div class="mark">网</div>
        <div>
          <div class="eyebrow">Training Method</div>
          <h1>网红训练法</h1>
        </div>
      </div>
      <div class="header-actions">
        <button id="historyToggle" class="mobile-history"
          type="button" aria-label="历史对话" aria-expanded="false"
          aria-controls="sidebar">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="1.7" stroke-linecap="round"
            aria-hidden="true">
            <path d="M4 7h16M4 12h16M4 17h10"></path>
          </svg>
        </button>
        <button id="viewToggle" class="view-toggle" type="button"
          aria-label="切换到手机版" title="切换到手机版">
          <span class="view-icon view-icon-mobile" aria-hidden="true">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="1.7" stroke-linecap="round"
              stroke-linejoin="round">
              <rect x="7" y="3" width="10" height="18" rx="2"></rect>
              <path d="M11 18h2"></path>
            </svg>
          </span>
          <span class="view-icon view-icon-desktop" aria-hidden="true">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="1.7" stroke-linecap="round"
              stroke-linejoin="round">
              <rect x="3" y="4" width="18" height="13" rx="2"></rect>
              <path d="M8 21h8M12 17v4"></path>
            </svg>
          </span>
          <span id="viewToggleLabel" class="view-toggle-label">手机版</span>
        </button>
        <div class="status">
          <span class="status-dot"></span>
          <span id="mode">正在连接</span>
        </div>
        <button id="reset" class="new-chat" type="button" aria-label="新对话">
          <span class="desktop-label">新对话</span>
          <span class="mobile-icon" aria-hidden="true">
            <svg width="21" height="21" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
              <path d="M12 5v14M5 12h14"></path>
            </svg>
          </span>
        </button>
      </div>
    </header>
    <main id="messages" aria-live="polite"></main>
    <div class="composer">
      <form id="form" class="composer-box">
        <textarea id="input" rows="1" maxlength="2000" placeholder="输入消息"></textarea>
        <button id="send" class="send" aria-label="发送">
          <svg width="19" height="19" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
            stroke-linejoin="round" aria-hidden="true">
            <path d="M12 19V5M6 11l6-6 6 6"></path>
          </svg>
        </button>
      </form>
      <div class="footnote">训练内容仅供专业训练参考</div>
    </div>
  </div>
</div>
<script>
const messages = document.querySelector('#messages');
const form = document.querySelector('#form');
const input = document.querySelector('#input');
const send = document.querySelector('#send');
const reset = document.querySelector('#reset');
const mode = document.querySelector('#mode');
const root = document.documentElement;
const mobileViewStyles = document.querySelector('#mobileViewStyles');
const viewToggle = document.querySelector('#viewToggle');
const viewToggleLabel = document.querySelector('#viewToggleLabel');
const viewChoiceButtons = [...document.querySelectorAll('[data-view-choice]')];
const sidebar = document.querySelector('#sidebar');
const sidebarBackdrop = document.querySelector('#sidebarBackdrop');
const historyToggle = document.querySelector('#historyToggle');
const sidebarClose = document.querySelector('#sidebarClose');
const newConversation = document.querySelector('#newConversation');
const conversationSearch = document.querySelector('#conversationSearch');
const conversationList = document.querySelector('#conversationList');
const VIEW_MODE_KEY = 'fitness_view_mode';
let sessionId = localStorage.getItem('fitness_chat_session') || null;
let searchTimer = null;

function esc(value) {
  const node = document.createElement('div');
  node.textContent = String(value ?? '');
  return node.innerHTML;
}

function escAttr(value) {
  return esc(value)
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function safeUrl(value) {
  const raw = String(value ?? '').replaceAll('&amp;', '&');
  if (!raw) return '';
  try {
    const url = new URL(raw, window.location.origin);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') return '';
    return escAttr(url.href);
  } catch {
    return '';
  }
}

function renderInline(value) {
  return esc(value)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,
      (_, label, url) => {
        const href = safeUrl(url);
        return href
          ? `<a href="${href}" target="_blank"
              rel="noopener noreferrer">${label}</a>`
          : label;
      });
}

function renderMarkdown(value) {
  const lines = String(value ?? '').replace(/\\r\\n?/g, '\\n').split('\\n');
  const html = [];
  let listType = '';
  const closeList = () => {
    if (listType) html.push(`</${listType}>`);
    listType = '';
  };
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      continue;
    }
    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      continue;
    }
    const unordered = trimmed.match(/^[-*]\s+(.+)$/);
    const ordered = trimmed.match(/^\d+\.\s+(.+)$/);
    if (unordered || ordered) {
      const wanted = unordered ? 'ul' : 'ol';
      if (listType !== wanted) {
        closeList();
        listType = wanted;
        html.push(`<${wanted}>`);
      }
      html.push(`<li>${renderInline((unordered || ordered)[1])}</li>`);
      continue;
    }
    closeList();
    const quote = trimmed.match(/^>\s?(.*)$/);
    if (quote) {
      html.push(`<blockquote>${renderInline(quote[1])}</blockquote>`);
    } else {
      html.push(`<p>${renderInline(trimmed)}</p>`);
    }
  }
  closeList();
  return html.join('');
}

function renderSources(sources) {
  if (!sources.length) return '';
  return `<div class="evidence">${sources.slice(0,6).map(source => {
    const url = ['linked', 'partial'].includes(source.source_status)
      ? safeUrl(source.source_url)
      : '';
    const detail = [
      source.speaker,
      source.timestamp,
      source.source_status === 'needs_source_link' ? '来源未核实' : ''
    ].filter(Boolean).join(' · ');
    const title = detail ? ` title="${escAttr(detail)}"` : '';
    const label = [
      source.citation ? esc(source.citation) : '',
      esc(source.name)
    ].filter(Boolean).join(' ');
    return url
      ? `<a class="tag" href="${url}" target="_blank"
          rel="noopener noreferrer"${title}>${label}</a>`
      : `<span class="tag"${title}>${label}</span>`;
  }).join('')}</div>`;
}

function emptyState() {
  messages.innerHTML = `
    <div class="empty">
      <div class="empty-ring">网</div>
      <h2>训练对话</h2>
      <p>说说你的目标、器械和每周训练频率，我来帮你整理训练思路。</p>
      <div class="suggestions" aria-label="快捷提问">
        <button class="prompt-chip" type="button"
          data-prompt="我想增肌，每周训练 3 天，应该怎么安排？">
          我想增肌，每周训练 3 天
        </button>
        <button class="prompt-chip" type="button"
          data-prompt="家里没有器械，怎么练胸？">
          家里没器械，怎么练胸？
        </button>
        <button class="prompt-chip" type="button"
          data-prompt="帮我安排一周训练计划，我刚开始健身。">
          帮我安排一周训练计划
        </button>
      </div>
    </div>`;
}

function addMessage(role, text, sources = [], requestId = null) {
  const empty = messages.querySelector('.empty');
  if (empty) empty.remove();
  const row = document.createElement('div');
  row.className = `message ${role}`;
  const tags = renderSources(sources);
  const reasons = [
    '没找到动作', '观点归属错误', '来源不可用',
    '回答太笼统', '建议有风险'
  ];
  const feedback = role === 'assistant' && requestId ? `
    <div class="feedback" data-request-id="${escAttr(requestId)}">
      <button type="button" data-feedback="1">有帮助</button>
      <button type="button" data-feedback="-1">没帮助</button>
      <span class="feedback-state"></span>
      <div class="feedback-more" hidden>
        ${reasons.map(reason =>
          `<button type="button" data-feedback="-1"
            data-reason="${escAttr(reason)}">${esc(reason)}</button>`
        ).join('')}
        <div class="feedback-comment">
          <input maxlength="1000" placeholder="补充说明（可选）">
          <button type="button" data-feedback-comment>提交备注</button>
        </div>
      </div>
    </div>` : '';
  row.innerHTML = `<div class="avatar">${role === 'user' ? '我' : '网'}</div>
    <div class="bubble">${renderMarkdown(text)}${tags}${feedback}</div>`;
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
  return row;
}

function addTyping() {
  const row = addMessage('assistant', '');
  row.querySelector('.bubble').innerHTML =
    '<span class="typing"><i></i><i></i><i></i></span>';
  return row;
}

function resizeInput() {
  input.style.height = 'auto';
  const maxHeight = window.matchMedia('(max-width:760px)').matches ? 120 : 150;
  input.style.height = `${Math.min(input.scrollHeight, maxHeight)}px`;
}

function openSidebar() {
  sidebar.classList.add('open');
  sidebarBackdrop.classList.add('open');
  historyToggle.setAttribute('aria-expanded', 'true');
  sidebarClose.focus({preventScroll:true});
}

function closeSidebar() {
  if (!sidebar.classList.contains('open')) return;
  sidebar.classList.remove('open');
  sidebarBackdrop.classList.remove('open');
  historyToggle.setAttribute('aria-expanded', 'false');
  historyToggle.focus({preventScroll:true});
}

function applyViewMode(view, persist = false) {
  const nextView = view === 'mobile' ? 'mobile' : 'desktop';
  const isMobile = nextView === 'mobile';
  root.dataset.view = nextView;
  mobileViewStyles.media = isMobile ? 'all' : 'not all';
  if (mobileViewStyles.sheet) {
    mobileViewStyles.sheet.disabled = !isMobile;
  }
  sidebar.classList.remove('open');
  sidebarBackdrop.classList.remove('open');
  historyToggle.setAttribute('aria-expanded', 'false');

  viewToggleLabel.textContent = isMobile ? '网页版' : '手机版';
  const actionLabel = isMobile ? '切换到网页版' : '切换到手机版';
  viewToggle.setAttribute('aria-label', actionLabel);
  viewToggle.title = actionLabel;
  viewChoiceButtons.forEach(button => {
    button.setAttribute(
      'aria-pressed', String(button.dataset.viewChoice === nextView)
    );
  });

  if (persist) {
    localStorage.setItem(VIEW_MODE_KEY, nextView);
    const url = new URL(window.location.href);
    url.searchParams.set('view', nextView);
    window.history.replaceState(null, '', url);
  }
  requestAnimationFrame(() => {
    syncAppHeight();
    resizeInput();
    messages.scrollTop = messages.scrollHeight;
  });
}

function initialViewMode() {
  const requested = new URL(window.location.href).searchParams.get('view');
  if (requested === 'mobile' || requested === 'desktop') {
    return requested;
  }
  const saved = localStorage.getItem(VIEW_MODE_KEY);
  if (saved === 'mobile' || saved === 'desktop') return saved;
  return window.matchMedia('(max-width:760px)').matches
    ? 'mobile' : 'desktop';
}

function syncAppHeight() {
  const height = window.visualViewport?.height || window.innerHeight;
  document.documentElement.style.setProperty(
    '--app-height', `${Math.round(height)}px`
  );
}

function formatHistoryTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('zh-CN', {
    month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit'
  }).format(date);
}

function renderConversations(items) {
  if (!items.length) {
    conversationList.innerHTML =
      '<div class="history-empty">暂无对话记录</div>';
    return;
  }
  conversationList.innerHTML = items.map(item => `
    <div class="conversation-item ${item.id === sessionId ? 'active' : ''}"
         data-id="${escAttr(item.id)}">
      <button class="conversation-main" data-action="open" type="button">
        <span class="conversation-title">${esc(item.title)}</span>
        <span class="conversation-preview">${esc(item.preview || '空对话')}</span>
        <time class="conversation-time">${esc(formatHistoryTime(item.updated_at))}
          · ${item.message_count} 条</time>
      </button>
      <div class="conversation-actions">
        <button data-action="rename" type="button" title="重命名">改</button>
        <button data-action="delete" type="button" title="删除">删</button>
      </div>
    </div>`).join('');
}

async function loadConversations() {
  const query = encodeURIComponent(conversationSearch.value.trim());
  try {
    const response = await fetch(`/api/chat/conversations?q=${query}`);
    if (!response.ok) throw new Error();
    const data = await response.json();
    renderConversations(data.conversations || []);
  } catch {
    conversationList.innerHTML =
      '<div class="history-empty">历史记录加载失败</div>';
  }
}

async function openConversation(id) {
  sessionId = id;
  localStorage.setItem('fitness_chat_session', sessionId);
  await loadHistory();
  await loadConversations();
  closeSidebar();
}

async function createConversation() {
  try {
    const response = await fetch('/api/chat/conversations', {method:'POST'});
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || '创建失败');
    sessionId = data.session_id;
    localStorage.setItem('fitness_chat_session', sessionId);
    emptyState();
    await loadConversations();
    closeSidebar();
    input.focus();
  } catch (error) {
    addMessage('assistant', `暂时无法创建对话：${error.message}`);
  }
}

async function loadHistory() {
  if (!sessionId) {
    emptyState();
    return;
  }
  try {
    const response = await fetch(
      `/api/chat/${encodeURIComponent(sessionId)}`
    );
    if (!response.ok) throw new Error();
    const data = await response.json();
    messages.innerHTML = '';
    if (!data.messages.length) throw new Error();
    data.messages.forEach(item =>
      addMessage(
        item.role, item.content, item.sources || [], item.request_id
      ));
  } catch {
    sessionId = null;
    localStorage.removeItem('fitness_chat_session');
    emptyState();
  }
}

async function loadStatus() {
  try {
    const response = await fetch('/api/chat/status');
    const data = await response.json();
    mode.textContent = data.llm_configured
      ? `DeepSeek · ${data.model}` : 'Local Engine';
  } catch {
    mode.textContent = 'Offline';
  }
}

async function sendFeedback(box, rating, reason = '', comment = '') {
  if (box.dataset.sent === '1') return;
  const state = box.querySelector('.feedback-state');
  state.textContent = '正在保存…';
  try {
    const response = await fetch('/api/feedback', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        request_id:box.dataset.requestId,
        rating,
        reason,
        comment
      })
    });
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || '保存失败');
    }
    box.dataset.sent = '1';
    box.dataset.reason = reason;
    state.textContent = '已记录';
    box.querySelectorAll('button').forEach(button => button.disabled = true);
  } catch (error) {
    state.textContent = error.message;
  }
}

messages.addEventListener('click', (event) => {
  const prompt = event.target.closest('.prompt-chip');
  if (prompt) {
    input.value = prompt.dataset.prompt || '';
    resizeInput();
    form.requestSubmit();
    return;
  }
  const button = event.target.closest('button[data-feedback], button[data-feedback-comment]');
  if (!button) return;
  const box = button.closest('.feedback');
  if (!box) return;

  if (button.hasAttribute('data-feedback-comment')) {
    const input = box.querySelector('.feedback-comment input');
    const reason = box.dataset.reason || '补充说明';
    sendFeedback(box, -1, reason, input.value.trim());
    return;
  }

  const rating = Number(button.dataset.feedback);
  const reason = button.dataset.reason || '';
  if (rating === -1 && !reason) {
    const more = box.querySelector('.feedback-more');
    more.hidden = false;
    button.classList.add('selected');
    return;
  }
  box.querySelectorAll('[data-feedback]').forEach(item =>
    item.classList.toggle('selected', item === button));
  if (reason) box.dataset.reason = reason;
  sendFeedback(box, rating, reason);
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  resizeInput();
  send.disabled = true;
  addMessage('user', text);
  const typing = addTyping();
  try {
    const response = await fetch('/api/chat', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:text, session_id:sessionId})
    });
    const data = await response.json();
    typing.remove();
    if (!response.ok) throw new Error(data.detail || '请求失败');
    sessionId = data.session_id;
    localStorage.setItem('fitness_chat_session', sessionId);
    addMessage(
      'assistant', data.answer, data.sources, data.request_id
    );
    await loadConversations();
  } catch (error) {
    typing.remove();
    addMessage('assistant', `暂时无法回复：${error.message}`);
  } finally {
    send.disabled = false;
    input.focus();
  }
});

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});

input.addEventListener('input', () => {
  resizeInput();
});

reset.addEventListener('click', createConversation);
newConversation.addEventListener('click', createConversation);
viewToggle.addEventListener('click', () => {
  const nextView = root.dataset.view === 'mobile' ? 'desktop' : 'mobile';
  applyViewMode(nextView, true);
});
viewChoiceButtons.forEach(button => {
  button.addEventListener('click', () => {
    applyViewMode(button.dataset.viewChoice, true);
  });
});
historyToggle.addEventListener('click', openSidebar);
sidebarClose.addEventListener('click', closeSidebar);
sidebarBackdrop.addEventListener('click', closeSidebar);

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeSidebar();
});

const mobileViewportQuery = window.matchMedia('(max-width:760px)');
mobileViewportQuery.addEventListener('change', (event) => {
  if (!localStorage.getItem(VIEW_MODE_KEY)) {
    applyViewMode(event.matches ? 'mobile' : 'desktop');
  }
});

conversationSearch.addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadConversations, 220);
});

conversationList.addEventListener('click', async (event) => {
  const button = event.target.closest('button[data-action]');
  const item = event.target.closest('.conversation-item');
  if (!button || !item) return;
  const id = item.dataset.id;
  const action = button.dataset.action;
  if (action === 'open') {
    await openConversation(id);
  } else if (action === 'rename') {
    const current = item.querySelector('.conversation-title').textContent;
    const title = window.prompt('重命名对话', current);
    if (!title || !title.trim()) return;
    await fetch(`/api/chat/conversations/${encodeURIComponent(id)}`, {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({title:title.trim()})
    });
    await loadConversations();
  } else if (action === 'delete') {
    if (!window.confirm('删除这条对话？')) return;
    await fetch(`/api/chat/${encodeURIComponent(id)}`, {method:'DELETE'});
    if (sessionId === id) {
      sessionId = null;
      localStorage.removeItem('fitness_chat_session');
      emptyState();
    }
    await loadConversations();
  }
});

async function initialize() {
  applyViewMode(initialViewMode());
  await loadStatus();
  await loadConversations();
  await loadHistory();
}

initialize();
resizeInput();
syncAppHeight();
window.addEventListener('resize', syncAppHeight);
window.addEventListener('orientationchange', syncAppHeight);
window.visualViewport?.addEventListener('resize', syncAppHeight);
window.visualViewport?.addEventListener('scroll', syncAppHeight);
</script>
</body>
</html>
"""
