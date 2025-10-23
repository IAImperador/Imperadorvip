import React, { useState } from "react";
import axios from "axios";

export default function RailwayConfig() {
  const [telegramToken, setTelegramToken] = useState("");
  const [chatId, setChatId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const API_BASE_URL = "https://imperadorvip-production.up.railway.app";

  const handleSave = async () => {
    try {
      setLoading(true);
      setError("");
      setMessage("");

      const payload = { telegram_token: telegramToken, chat_id: chatId };

      const response = await axios.put(`${API_BASE_URL}/bot/config`, payload, {
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
      });

      if (response.status === 200) setMessage("✅ Configuração salva com sucesso!");
    } catch (err) {
      setError("❌ Erro ao salvar: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleToggleBot = async (enable) => {
    try {
      setLoading(true);
      const endpoint = enable ? "/bot/enable" : "/bot/disable";
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, null, {
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
      });

      if (response.status === 200)
        setMessage(enable ? "🤖 Bot ativado!" : "⛔ Bot desativado!");
    } catch (err) {
      setError("❌ Erro: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleTestAnalysis = async () => {
    try {
      setLoading(true);
      const response = await axios.post(
        `${API_BASE_URL}/analyze`,
        { symbol: "EUR/USD", interval: "1min" },
        { headers: { "x-api-key": "imperadorvip-secure-key-2025" } }
      );
      setMessage("✅ Resultado: " + JSON.stringify(response.data));
    } catch (err) {
      setError("❌ Erro: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold text-yellow-400 mb-4">⚙️ IA do Imperador</h2>

      <label>Token Telegram:</label>
      <input className="w-full p-2 rounded bg-gray-800 mb-2"
        value={telegramToken} onChange={(e) => setTelegramToken(e.target.value)} />

      <label>Chat ID Telegram:</label>
      <input className="w-full p-2 rounded bg-gray-800 mb-4"
        value={chatId} onChange={(e) => setChatId(e.target.value)} />

      <button onClick={handleSave} className="bg-green-600 w-full p-2 rounded mb-4">
        💾 Salvar Configuração
      </button>

      <div className="flex justify-between mb-4">
        <button onClick={() => handleToggleBot(true)} className="bg-blue-600 px-4 py-2 rounded">Ativar Bot</button>
        <button onClick={() => handleToggleBot(false)} className="bg-red-600 px-4 py-2 rounded">Desativar Bot</button>
      </div>

      <button onClick={handleTestAnalysis} className="bg-yellow-600 w-full p-2 rounded">
        ⚡ Testar Análise
      </button>

      {message && <p className="mt-4 text-green-400">{message}</p>}
      {error && <p className="mt-4 text-red-400">{error}</p>}
    </div>
  );
}
