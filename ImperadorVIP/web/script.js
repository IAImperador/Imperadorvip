const $ = (sel) => document.querySelector(sel);
const apiUrl = $("#apiUrl");
const apiKey = $("#apiKey");
const out = $("#out");
apiUrl.value = "http://localhost:8080";
function show(json){ out.textContent = JSON.stringify(json, null, 2); }
async function call(path, method="GET", body=null){
  const url = apiUrl.value.replace(/\/$/,'') + path;
  const opts = { method, headers: { "Content-Type":"application/json" } };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(url, opts);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return await r.json();
}
$("#btnStatus").onclick = async () => { try{ show(await call("/status")); }catch(e){ show({error:String(e)}); } }
$("#btnToggle").onclick = async () => { try{ show(await call("/toggle","POST",{ api_key: apiKey.value })); }catch(e){ show({error:String(e)}); } }
document.querySelectorAll("button.mode").forEach(btn=>{
  btn.onclick = async () => { try{ show(await call("/mode","POST",{ api_key: apiKey.value, mode: btn.dataset.mode })); }catch(e){ show({error:String(e)}); } }
});
document.querySelectorAll("button.market").forEach(btn=>{
  btn.onclick = async () => { try{ show(await call("/market","POST",{ api_key: apiKey.value, market: btn.dataset.market })); }catch(e){ show({error:String(e)}); } }
});
$("#btnSignal").onclick = async () => {
  try{
    const resp = await call("/signal","POST",{
      api_key: apiKey.value,
      symbol: $("#symbol").value.trim(),
      timeframe: $("#timeframe").value,
      min_confidence: parseInt($("#minConf").value||"90",10)
    });
    show(resp);
  }catch(e){ show({error:String(e)}); }
}
