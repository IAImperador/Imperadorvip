import React, { useState } from "react";
import axios from "axios";

export default function RailwayConfig() {
  const [baseUrl, setBaseUrl] = useState("https://imperadorvip-production.up.railway.app");
  const [apiKey, setApiKey] = useState("imperadorvip-secure-key-2025");

  const [telegramToken, setTelegramToken] = useState("");
  const [chatId, setChatId] = useState("@IAdoimperador");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const headers = { "x-api-key": apiKey };

  const handleHealth = async () => {
    try {
      setLoading(true); setError(""); setMessage("");
      const r = await axios.get(`${baseUrl}/health`);
      setMessage(`✅ Conexão OK: ${JSON.stringify(r.data)}`);
    } catch (err) {
      setError(`❌ Falha na conexão: ${err.response?.status} - ${JSON.stringify(err.response?.data || err.message)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true); setError(""); setMessage("");
      const payload = {
        telegram_token: telegramToken || null,
        chat_id: chatId || null,
      };
      const r = await axios.post(`${baseUrl}/bot/config`, payload, { headers });
      if (r.status === 200) setMessage("✅ Configuração salva!");
      else setError("⚠️ Falha ao salvar configuração.");
    } catch (err) {
      setError(`❌ Erro: ${JSON.stringify(err.response?.data || err.message)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleBot = async (enable) => {
    try {
      setLoading(true); setError(""); setMessage("");
      const endpoint = enable ? "/bot/enable" : "/bot/disable";
      const r = await axios.post(`${baseUrl}${endpoint}`, null, { headers });
      if (r.status === 200) setMessage(enable ? "🤖 Bot ativado!" : "⛔ Bot desativado!");
      else setError("⚠️ Erro ao alternar bot.");
    } catch (err) {
      setError(`❌ Erro ao alternar bot: ${err.response?.status} - ${JSON.stringify(err.response?.data || err.message)}`);
    } finally {
      setLoading(false);
    }
  };

  const handleTestAnalysis = async () => {
    try {
      setLoading(true); setError(""); setMessage("");
      const payload = { symbol: "EUR/USD", interval: "1min", auto_send: false };
      const r = await axios.post(`${baseUrl}/analyze`, payload, { headers });
      const { result } = r.data || {};
      setMessage(`✅ Análise OK! Sinal: ${result?.signal} (${result?.confidence}%)`);
    } catch (err) {
      setError(`❌ Erro na análise: ${JSON.stringify(err.response?.data || err.message)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-900 text-white rounded-xl shadow-lg space-y-6">
      <h2 className="text-2xl font-bold text-yellow-400">⚙️ IA do Imperador</h2>

      {/* URL + API KEY */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block mb-2">URL do Railway</label>
          <input value={baseUrl} onChange={e => setBaseUrl(e.target.value)} className="w-full p-2 rounded bg-gray-800 border border-gray-700" />
        </div>
        <div>
          <label className="block mb-2">API Key (x-api-key)</label>
          <input value={apiKey} onChange={e => setApiKey(e.target.value)} className="w-full p-2 rounded bg-gray-800 border border-gray-700" />
        </div>
      </div>

      <button onClick={handleHealth} disabled={loading} className="bg-slate-600 hover:bg-slate-700 px-4 py-2 rounded">
        🔌 Testar conexão
      </button>

      <hr className="border-gray-700" />

      {/* Telegram */}
      <div>
        <h3 className="text-xl font-semibold mb-3">Controle do Bot Telegram</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block mb-2">Token Telegram (Opcional)</label>
            <input value={telegramToken} onChange={e => setTelegramToken(e.target.value)} className="w-full p-2 rounded bg-gray-800 border border-gray-700" />
          </div>
          <div>
            <label className="block mb-2">Chat ID Telegram</label>
            <input value={chatId} onChange={e => setChatId(e.target.value)} className="w-full p-2 rounded bg-gray-800 border border-gray-700" />
          </div>
        </div>
        <div className="flex gap-3 mt-3">
          <button onClick={handleSave} disabled={loading} className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded">💾 Salvar Configuração</button>
          <button onClick={() => handleToggleBot(true)} className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">🟢 Ativar Bot</button>
          <button onClick={() => handleToggleBot(false)} className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded">🔴 Desativar Bot</button>
        </div>
      </div>

      <hr className="border-gray-700" />

      {/* Teste TwelveData */}
      <div>
        <h3 className="text-xl font-semibold mb-3">Testar Análise EUR/USD (TwelveData)</h3>
        <button onClick={handleTestAnalysis} disabled={loading} className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded w-full">
          ⚡ Testar Análise com Dados Reais
        </button>
      </div>

      {message && <p className="mt-2 text-green-400">{message}</p>}
      {error && <p className="mt-2 text-red-400">{error}</p>}
    </div>
  );
}

