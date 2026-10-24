"""Tiny web page: paste a job, get a score and a proposal draft. Standard library only."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import core

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Upwork Radar</title>
<style>
:root{--bg:#f6f7f5;--card:#fff;--fg:#1c1f1a;--mute:#6b7166;--line:#dfe3dc;--acc:#14a800;--warn:#b54708;--bad:#b42318}
@media (prefers-color-scheme:dark){:root{--bg:#121411;--card:#1b1e1a;--fg:#e8ebe5;--mute:#9aa194;--line:#2c3129;--acc:#3ccf2a;--warn:#f79009;--bad:#f97066}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
main{max-width:860px;margin:0 auto;padding:20px 16px 60px}h1{font-size:20px;margin:0 0 14px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin-bottom:14px}
textarea,input{width:100%;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:10px;font:inherit}
textarea{min-height:180px;resize:vertical}input{margin-bottom:10px}
button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:9px 16px;font:inherit;font-weight:600;cursor:pointer}
button.ghost{background:transparent;color:var(--fg);border:1px solid var(--line)}button:disabled{opacity:.5}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:10px}
.score{font-size:28px;font-weight:700}.apply{color:var(--acc)}.maybe{color:var(--warn)}.skip{color:var(--bad)}
.mute{color:var(--mute);font-size:13px}ul{margin:6px 0;padding-left:20px}
.h{display:flex;justify-content:space-between;gap:10px;padding:8px 0;border-top:1px solid var(--line);cursor:pointer}
.h:first-child{border-top:0}.pill{font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 8px}
</style></head><body><main>
<h1>Upwork Radar</h1>
<div class="card">
<input id="url" placeholder="Job link (optional)">
<textarea id="job" placeholder="Paste the whole job post here: title, description, budget, client info..."></textarea>
<div class="row"><button id="go">Score + draft</button><span id="msg" class="mute"></span></div>
</div>
<div id="out"></div>
<div class="card"><b>History</b><div id="hist" class="mute">Loading...</div></div>
</main><script>
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function show(r){
  const li=a=>a.length?"<ul>"+a.map(x=>"<li>"+esc(x)+"</li>").join("")+"</ul>":"<div class=mute>none</div>";
  $("#out").innerHTML=`<div class="card"><div class="row" style="margin:0"><span class="score ${r.verdict}">${r.score}/10</span>
  <b class="${r.verdict}">${esc(r.verdict).toUpperCase()}</b><span class="pill">${esc(r.niche)}</span>
  <span class="pill">${esc(r.status||"new")}</span></div>
  <div style="margin-top:6px"><b>${esc(r.title)}</b> ${r.url?`<a href="${esc(r.url)}" target="_blank" rel="noopener">open</a>`:""}</div>
  <div class="row" style="display:block"><b>Why</b>${li(r.reasons)}<b>Red flags</b>${li(r.red_flags)}</div>
  ${r.proposal?`<b>Proposal</b><textarea id="prop">${esc(r.proposal)}</textarea>
  <div class="row"><button id="copy">Copy</button><button class="ghost" data-s="sent">Mark sent</button>
  <button class="ghost" data-s="ignored">Ignore</button></div>`:`<div class="row"><button class="ghost" data-s="ignored">Ignore</button></div>`}</div>`;
  const c=$("#copy");if(c)c.onclick=()=>{navigator.clipboard.writeText($("#prop").value);c.textContent="Copied"};
  document.querySelectorAll("[data-s]").forEach(b=>b.onclick=async()=>{
    await fetch("/api/status",{method:"POST",body:JSON.stringify({id:r.id,status:b.dataset.s})});r.status=b.dataset.s;show(r);hist()});
}
let H=[];
async function hist(){
  H=await (await fetch("/api/history")).json();
  $("#hist").innerHTML=H.length?H.map((r,i)=>`<div class="h" data-i="${i}"><span>${esc(r.title||"(untitled)")}
  <span class="mute">${esc(r.created)}</span></span><span><b class="${r.verdict}">${r.score}</b> <span class="pill">${esc(r.status)}</span></span></div>`).join(""):"Nothing yet.";
  document.querySelectorAll(".h").forEach(e=>e.onclick=()=>{show(H[e.dataset.i]);scrollTo(0,0)});
}
$("#go").onclick=async()=>{
  const job=$("#job").value.trim();if(!job)return;
  $("#go").disabled=true;$("#msg").textContent="Thinking (10-40 s)...";
  try{const r=await fetch("/api/score",{method:"POST",body:JSON.stringify({job,url:$("#url").value})});
    const d=await r.json();if(!r.ok)throw new Error(d.error);show(d);$("#job").value="";$("#url").value="";$("#msg").textContent="";hist()}
  catch(e){$("#msg").textContent="Error: "+e.message}
  $("#go").disabled=false;
};
hist();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body, ctype: str = "application/json") -> None:
        data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        if self.path == "/":
            self._send(200, PAGE, "text/html")
        elif self.path == "/api/history":
            self._send(200, core.history())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        try:
            body = self._json()
            if self.path == "/api/score":
                self._send(200, core.score_job(body.get("job", ""), body.get("url", "")))
            elif self.path == "/api/status":
                core.set_status(int(body["id"]), body["status"])
                self._send(200, {"ok": True})
            else:
                self._send(404, {"error": "not found"})
        except Exception as e:  # report to the page instead of dropping the connection
            self._send(500, {"error": str(e)})


def serve(host: str, port: int) -> None:
    print(f"Upwork Radar on http://{host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
