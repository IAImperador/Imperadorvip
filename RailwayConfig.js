import React, { useState } from "react";
import axios from "axios";

export default function RailwayConfig() {
  const [apiBase, setApiBase] = useState("https://imperadorvip-production.up.railway.app");
  const [apiKey, setApiKey] = useState("imperadorvip-secure-key-2025");

  const [telegramToken, setTelegramToken] = useState("");
  const [chatId, setChatId] = useState("");

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // ---------- Helpers ----------
  const h = axios.create({
    baseURL: apiBase.replace(/\/+$/, ""),
    timeout: 20000,
  });

  const authHeaders = { "x-api-key": apiKey };

  const showErr = (prefix, err) => {
    const detail = err?.response?.data?.detail ?? err?.message ?? String(err);
    setError(`${prefix}: ${detail}`);
  };

  // ---------- Testar conexão ----------
  const handleTest = async () => {
    setError(""); setMessage(""); setLoading(true);
    try {
      const r = await h.get("/health");
      if (r?.data?.ok) setMessage("✅ Conectado ao backend!");
      else setError("⚠️ Backend respondeu, mas sem ok=true.");
    } catch (e) {
      showErr("❌ Erro de conexão", e);
    } finally {
      setLoading(false);
    }
  };

  // ---------- Salvar config bot ----------
  const handleSave = async () => {
    setError(""); setMessage(""); setLoading(true);
    try {
      const payload = {
        telegram_token: telegramToken || null,
        chat_id: chatId || null,
      };
      const r = await h.post("/bot/config", payload, { headers: authHeaders });
      if (r?.data?.ok) setMessage("✅ Configuração salva!");
      else setError("⚠️ Falha ao salvar configuração.");
    } catch (e) {
      showErr("❌ Erro ao salvar configuração", e);
    } finally {
      setLoading(false);
    }
  };

  // ---------- Alternar bot ----------
  const handleToggleBot = async (enable) => {
    setError(""); setMessage(""); setLoading(true);
    try {
      const endpoint = enable ? "/bot/enable" : "/bot/disable";
      const r = await h.post(endpoint, null, { headers: authHeaders });
      if (r?.data?.ok) {
        setMessage(enable ? "🤖 Bot ativado!" : "⛔ Bot desativado!");
      } else {
        setError("⚠️ Erro ao alternar bot.");
      }
    } catch (e) {
      showErr("❌ Erro ao alternar bot", e);
    } finally {
      setLoading(false);
    }
  };

  // ---------- Testar análise ----------
  const handleTestAnalysis = async () => {
    setError(""); setMessage(""); setLoading(true);
    try {
      const payload = { symbol: "EUR/USD", interval: "1min" };
      const r = await h.post("/analyze", payload, { headers: authHeaders });
      const d = r?.data;
      if (d?.signal) {
        setMessage(`✅ Análise OK! Sinal: ${d.signal} (${d.confidence}%) • Preço: ${d.price}`);
      } else {
        setError("⚠️ Resposta sem sinal.");
      }
    } catch (e) {
      showErr("❌ Erro na análise", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-900 text-white rounded-xl shadow-lg space-y-4">
      <h2 className="text-2xl font-bold text-yellow-400">⚙️ IA do Imperador</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block mb-1">URL do Railway</label>
          <input
            className="w-full p-2 rounded bg-gray-800 border border-gray-700"
            value={apiBase}
            onChange={(e) => setApiBase(e.target.value)}
            placeholder="https://...railway.app"
          />
        </div>
        <div>
          <label className="block mb-1">API Key (x-api-key)</label>
          <input
            className="w-full p-2 rounded bg-gray-800 border border-gray-700"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder="imperadorvip-secure-key-2025"
          />
        </div>
      </div>

      <button
        onClick={handleTest}
        disabled={loading}
        className="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded w-full"
      >
        {loading ? "Testando..." : "🔌 Testar Conexão (/health)"}
      </button>

      <hr className="border-gray-700" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <label className="block mb-1">Token Telegram (Opcional)</label>
          <input
            className="w-full p-2 rounded bg-gray-800 border border-gray-700"
            value={telegramToken}
            onChange={(e) => setTelegramToken(e.target.value)}
            placeholder="123456:ABC..."
          />
        </div>
        <div>
          <label className="block mb-1">Chat ID Telegram</label>
          <input
            className="w-full p-2 rounded bg-gray-800 border border-gray-700"
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            placeholder="@IAdoimperador"
          />
        </div>
      </div>

      <button
        onClick={handleSave}
        disabled={loading}
        className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded w-full"
      >
        {loading ? "Salvando..." : "💾 Salvar Configuração"}
      </button>

      <div className="flex gap-3">
        <button
          onClick={() => handleToggleBot(true)}
          className="flex-1 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
        >
          🟢 Ativar Bot
        </button>
        <button
          onClick={() => handleToggleBot(false)}
          className="flex-1 bg-red-600 hover:bg-red-700 px-4 py-2 rounded"
        >
          🔴 Desativar Bot
        </button>
      </div>

      <button
        onClick={handleTestAnalysis}
        disabled={loading}
        className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded w-full"
      >
        ⚡ Testar Análise (EUR/USD • 1min)
      </button>

      {message && <p className="mt-2 text-green-400">{message}</p>}
      {error && <p className="mt-2 text-red-400">{error}</p>}
    </div>
  );
}
