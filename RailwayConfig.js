import React, { useState } from "react";
import axios from "axios";

export default function RailwayConfig() {
  const [telegramToken, setTelegramToken] = useState("");
  const [chatId, setChatId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // ✅ URL correta do backend
  const API_BASE_URL = "https://imperadorvip-production.up.railway.app";

  // 🔁 Função de requisição com timeout manual
  const apiRequest = async (method, endpoint, data = null) => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    try {
      const response = await axios({
        method,
        url: `${API_BASE_URL}${endpoint}`,
        data,
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
        signal: controller.signal,
      });
      clearTimeout(timeout);
      return response;
    } catch (err) {
      clearTimeout(timeout);
      throw new Error(err.response?.data?.detail || err.message);
    }
  };

  const handleSave = async () => {
    try {
      setLoading(true);
      setMessage("");
      setError("");
      const payload = {
        telegram_token: telegramToken || null,
        chat_id: chatId || null,
      };
      const res = await apiRequest("post", "/bot/config", payload);
      setMessage("✅ Configuração salva com sucesso!");
    } catch (err) {
      setError("❌ Falha ao salvar: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleBot = async (enable) => {
    try {
      setLoading(true);
      setError("");
      setMessage("");
      const endpoint = enable ? "/bot/enable" : "/bot/disable";
      const res = await apiRequest("post", endpoint);
      setMessage(
        enable ? "🤖 Bot ativado com sucesso!" : "⛔ Bot desativado com sucesso!"
      );
    } catch (err) {
      setError("❌ Erro ao alternar bot: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTestAnalysis = async () => {
    try {
      setLoading(true);
      setError("");
      setMessage("");
      const payload = { symbol: "EUR/USD", interval: "1min" };
      const res = await apiRequest("post", "/analyze", payload);
      if (res.data) {
        setMessage(
          "✅ Análise OK! Sinal: " +
            res.data.signal +
            " (" +
            res.data.confidence +
            "%)"
        );
      } else {
        setError("⚠️ Sem dados retornados do backend.");
      }
    } catch (err) {
      setError("❌ Erro na análise: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold text-yellow-400 mb-4">
        ⚙️ IA do Imperador
      </h2>

      <div className="mb-4">
        <label className="block mb-2">Token Telegram (Opcional)</label>
        <input
          type="text"
          value={telegramToken}
          onChange={(e) => setTelegramToken(e.target.value)}
          className="w-full p-2 rounded bg-gray-800 border border-gray-700"
          placeholder="Insira o Token do Bot"
        />
      </div>

      <div className="mb-4">
        <label className="block mb-2">Chat ID Telegram</label>
        <input
          type="text"
          value={chatId}
          onChange={(e) => setChatId(e.target.value)}
          className="w-full p-2 rounded bg-gray-800 border border-gray-700"
          placeholder="@IAdoimperador"
        />
      </div>

      <button
        onClick={handleSave}
        disabled={loading}
        className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded w-full"
      >
        {loading ? "Salvando..." : "💾 Salvar Configuração"}
      </button>

      <hr className="my-6 border-gray-700" />

      <div className="flex justify-between mb-4">
        <button
          onClick={() => handleToggleBot(true)}
          className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded"
        >
          🟢 Ativar Bot
        </button>
        <button
          onClick={() => handleToggleBot(false)}
          className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded"
        >
          🔴 Desativar Bot
        </button>
      </div>

      <hr className="my-6 border-gray-700" />

      <button
        onClick={handleTestAnalysis}
        disabled={loading}
        className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded w-full"
      >
        ⚡ Testar Análise com Dados Reais
      </button>

      {message && <p className="mt-4 text-green-400">{message}</p>}
      {error && <p className="mt-4 text-red-400">{error}</p>}
    </div>
  );
}
