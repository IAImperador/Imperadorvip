import React, { useState } from "react";
import axios from "axios";

export default function RailwayConfig() {
  const [telegramToken, setTelegramToken] = useState("");
  const [chatId, setChatId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // ✅ URL do backend no Railway
  const API_BASE_URL = "https://imperadorvip-production.up.railway.app";

  // ===================================================
  // 🔧 SALVAR CONFIGURAÇÃO DO TELEGRAM
  // ===================================================
  const handleSave = async () => {
    try {
      setLoading(true);
      setError("");
      setMessage("");

      const payload = {
        telegram_token: telegramToken,
        chat_id: chatId,
      };

      const response = await axios.post(`${API_BASE_URL}/bot/config`, payload, {
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
      });

      setMessage(response.data.message || "✅ Configuração salva com sucesso!");
    } catch (err) {
      console.error("Erro ao salvar config:", err);
      setError(
        "❌ Erro ao salvar configuração: " +
          (err.response?.data?.detail || err.message)
      );
    } finally {
      setLoading(false);
    }
  };

  // ===================================================
  // 🤖 ATIVAR / DESATIVAR BOT
  // ===================================================
  const handleToggleBot = async (enable) => {
    try {
      setLoading(true);
      setError("");
      setMessage("");

      const endpoint = enable ? "/bot/enable" : "/bot/disable";
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, null, {
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
      });

      setMessage(response.data.message || "✅ Operação concluída!");
    } catch (err) {
      console.error("Erro ao alternar bot:", err);
      setError(
        "❌ Erro ao alternar bot: " +
          (err.response?.data?.detail || err.message)
      );
    } finally {
      setLoading(false);
    }
  };

  // ===================================================
  // ⚡ TESTE DE ANÁLISE EM TEMPO REAL
  // ===================================================
  const handleTestAnalysis = async () => {
    try {
      setLoading(true);
      setError("");
      setMessage("");

      const payload = {
        symbol: "EUR/USD",
        interval: "1min",
      };

      const response = await axios.post(`${API_BASE_URL}/analyze`, payload, {
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
      });

      if (response.data && response.data.signal) {
        setMessage(
          `✅ Análise OK! Sinal: ${response.data.signal} (${response.data.confidence}%)`
        );
      } else {
        setError("⚠️ Nenhum sinal retornado pela IA (verifique o backend).");
      }
    } catch (err) {
      console.error("Erro na análise:", err);
      setError(
        "❌ Erro na análise: " +
          (err.response?.data?.detail || err.message)
      );
    } finally {
      setLoading(false);
    }
  };

  // ===================================================
  // 💻 INTERFACE
  // ===================================================
  return (
    <div className="p-6 bg-gray-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold text-yellow-400 mb-4">
        ⚙️ IA do Imperador - Painel de Controle
      </h2>

      <div className="mb-4">
        <label className="block mb-2">Token do Bot Telegram</label>
        <input
          type="text"
          value={telegramToken}
          onChange={(e) => setTelegramToken(e.target.value)}
          className="w-full p-2 rounded bg-gray-800 border border-gray-700"
          placeholder="7651355...Uab4"
        />
      </div>

      <div className="mb-4">
        <label className="block mb-2">Chat ID (Ex: @IAdoimperador)</label>
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
        className="bg-green-600 hover:bg-green-700 px-4 py-2 rounded w-full mb-4"
      >
        {loading ? "Salvando..." : "💾 Salvar Configuração"}
      </button>

      <div className="flex justify-between mb-4">
        <button
          onClick={() => handleToggleBot(true)}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded w-1/2 mr-2"
        >
          🟢 Ativar Bot
        </button>

        <button
          onClick={() => handleToggleBot(false)}
          disabled={loading}
          className="bg-red-600 hover:bg-red-700 px-4 py-2 rounded w-1/2 ml-2"
        >
          🔴 Desativar Bot
        </button>
      </div>

      <button
        onClick={handleTestAnalysis}
        disabled={loading}
        className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded w-full"
      >
        ⚡ Testar Análise em Tempo Real
      </button>

      {message && <p className="mt-4 text-green-400">{message}</p>}
      {error && <p className="mt-4 text-red-400">{error}</p>}
    </div>
  );
}
