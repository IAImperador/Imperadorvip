import React, { useState } from "react";
import axios from "axios";

export default function RailwayConfig() {
  const [telegramToken, setTelegramToken] = useState("");
  const [chatId, setChatId] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  // 🔗 URL do seu backend (Railway)
  const API_BASE_URL = "https://imperadorvip-production.up.railway.app";

  // ================================
  // SALVAR CONFIGURAÇÃO DO BOT
  // ================================
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

      if (response.status === 200) {
        setMessage("✅ Configuração salva com sucesso!");
      } else {
        setError("⚠️ Falha ao salvar configuração.");
      }
    } catch (err) {
      setError("❌ Erro: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // ================================
  // ATIVAR / DESATIVAR BOT
  // ================================
  const handleToggleBot = async (enable) => {
    try {
      setLoading(true);
      setError("");
      setMessage("");

      const endpoint = enable ? "/bot/start" : "/bot/stop";
      const response = await axios.post(`${API_BASE_URL}${endpoint}`, null, {
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
      });

      if (response.status === 200) {
        setMessage(
          enable
            ? "🤖 Bot ativado com sucesso!"
            : "⛔ Bot desativado com sucesso!"
        );
      } else {
        setError("⚠️ Erro ao alternar o estado do bot.");
      }
    } catch (err) {
      setError("❌ Erro ao alternar bot: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // ================================
  // TESTAR ANÁLISE DE SINAL (REAL)
  // ================================
  const handleTestAnalysis = async () => {
    try {
      setLoading(true);
      setError("");
      setMessage("Analisando mercado em tempo real...");

      const payload = {
        symbol: "EUR/USD",
        interval: "1min",
        broker: "Quotex",
      };

      const response = await axios.post(`${API_BASE_URL}/analyze`, payload, {
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
      });

      if (response.data) {
        const signal = response.data.signal || "WAIT";
        const confidence = response.data.confidence || "0";
        setMessage(`✅ Análise OK! Sinal: ${signal} (${confidence}%)`);
      } else {
        setError("⚠️ Falha ao processar a análise.");
      }
    } catch (err) {
      setError("❌ Erro na análise: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  // ================================
  // TESTAR SINAL AO VIVO (live)
  // ================================
  const handleLiveSignal = async () => {
    try {
      setLoading(true);
      setError("");
      setMessage("Buscando sinais ao vivo...");

      const response = await axios.get(`${API_BASE_URL}/signal/live`, {
        headers: { "x-api-key": "imperadorvip-secure-key-2025" },
      });

      if (response.data && response.data.signal) {
        setMessage(
          `📈 Sinal ao vivo: ${response.data.signal} (${response.data.confidence}%)`
        );
      } else {
        setError("⚠️ Nenhum sinal ativo no momento.");
      }
    } catch (err) {
      setError("❌ Erro no fetch: " + (err.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-gray-900 text-white rounded-xl shadow-lg">
      <h2 className="text-2xl font-bold text-yellow-400 mb-4">⚙️ IA do Imperador</h2>

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

      <div className="space-y-3">
        <button
          onClick={handleTestAnalysis}
          disabled={loading}
          className="bg-yellow-600 hover:bg-yellow-700 px-4 py-2 rounded w-full"
        >
          ⚡ Testar Análise com Dados Reais
        </button>

        <button
          onClick={handleLiveSignal}
          disabled={loading}
          className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded w-full"
        >
          🔔 Ver Sinal Ao Vivo
        </button>
      </div>

      {message && <p className="mt-4 text-green-400">{message}</p>}
      {error && <p className="mt-4 text-red-400">{error}</p>}
    </div>
  );
}
