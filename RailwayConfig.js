// ==============================================
// IA DO IMPERADOR - RAILWAY CONFIG DASHBOARD
// Base44 + FastAPI (Railway) + TwelveData + Telegram
// ==============================================

import React, { useState, useEffect } from "react";
import axios from "axios";

const API_BASE_URL = "https://imperadorvip-production.up.railway.app";

export default function RailwayConfig() {
  const [status, setStatus] = useState("Desconectado");
  const [twelveKey, setTwelveKey] = useState("");
  const [botStatus, setBotStatus] = useState(false);
  const [signal, setSignal] = useState(null);
  const [confidence, setConfidence] = useState(0);
  const [loading, setLoading] = useState(false);

  // =========================
  // FUNÇÃO PARA TESTAR API
  // =========================
  const testarConexao = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/signal/live`);
      if (res.data.status === "ok") {
        setStatus("✅ Conectado com sucesso");
        setSignal(res.data.sinal);
        setConfidence(res.data.sinal.confiança);
      } else {
        setStatus("⚠️ Nenhum sinal disponível");
      }
    } catch (err) {
      console.error(err);
      setStatus("❌ Erro de conexão com a API");
    } finally {
      setLoading(false);
    }
  };

  // =========================
  // FUNÇÃO PARA TESTAR ANALISE REAL (TwelveData)
  // =========================
  const testarAnalise = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API_BASE_URL}/signal/live`);
      if (res.data?.sinal) {
        setSignal(res.data.sinal);
        setConfidence(res.data.sinal.confiança);
      }
    } catch (err) {
      setStatus("❌ Falha ao buscar dados reais");
    } finally {
      setLoading(false);
    }
  };

  // =========================
  // FUNÇÃO PARA ATIVAR / DESATIVAR BOT
  // =========================
  const alternarBot = async () => {
    try {
      const novaAcao = !botStatus;
      const res = await axios.post(`${API_BASE_URL}/bot/status`, {
        ativo: novaAcao,
      });
      if (res.status === 200) {
        setBotStatus(novaAcao);
        alert(
          novaAcao
            ? "🤖 Bot ativado com sucesso! (envio a cada 5 minutos)"
            : "🛑 Bot desativado."
        );
      }
    } catch (err) {
      console.error(err);
      alert("Erro ao alternar bot (verifique API no Railway)");
    }
  };

  // =========================
  // REQUISIÇÃO AUTOMÁTICA A CADA 5 MINUTOS
  // =========================
  useEffect(() => {
    if (botStatus) {
      const intervalo = setInterval(() => {
        testarAnalise();
      }, 5 * 60 * 1000); // 5 minutos
      return () => clearInterval(intervalo);
    }
  }, [botStatus]);

  return (
    <div className="bg-black text-white p-6 rounded-2xl shadow-xl max-w-4xl mx-auto border border-yellow-500">
      <h1 className="text-3xl font-bold text-yellow-400 mb-6 text-center">
        👑 IA do Imperador 4.0 + Railway + TwelveData + Telegram
      </h1>

      {/* STATUS DE CONEXÃO */}
      <div className="bg-gray-900 p-4 rounded-xl mb-5">
        <h2 className="text-xl mb-2 text-yellow-300 font-semibold">
          Status da Conexão:
        </h2>
        <p>{status}</p>
        <button
          onClick={testarConexao}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-yellow-500 text-black font-bold rounded hover:bg-yellow-400"
        >
          {loading ? "Testando..." : "Testar Conexão com Railway"}
        </button>
      </div>

      {/* CONTROLE DO BOT TELEGRAM */}
      <div className="bg-gray-900 p-4 rounded-xl mb-5">
        <h2 className="text-xl mb-2 text-yellow-300 font-semibold">
          Controle do Bot Telegram
        </h2>
        <button
          onClick={alternarBot}
          className={`px-4 py-2 font-bold rounded ${
            botStatus
              ? "bg-red-600 hover:bg-red-500"
              : "bg-green-500 hover:bg-green-400"
          }`}
        >
          {botStatus ? "Desativar Bot" : "Ativar Bot"}
        </button>
      </div>

      {/* TESTE TWELVEDATA */}
      <div className="bg-gray-900 p-4 rounded-xl mb-5">
        <h2 className="text-xl mb-2 text-yellow-300 font-semibold">
          Testar Análise EUR/USD (TwelveData)
        </h2>
        <button
          onClick={testarAnalise}
          disabled={loading}
          className="mt-3 px-4 py-2 bg-yellow-500 text-black font-bold rounded hover:bg-yellow-400"
        >
          {loading ? "Carregando..." : "Testar Análise com Dados Reais"}
        </button>
      </div>

      {/* RESULTADO DO SINAL */}
      {signal && (
        <div className="bg-gray-800 p-4 rounded-xl border border-yellow-600">
          <h3 className="text-lg font-semibold text-yellow-400 mb-2">
            Último Sinal Detectado:
          </h3>
          <p>
            <strong>Ativo:</strong> {signal.ativo} <br />
            <strong>Sinal:</strong> {signal.sinal} <br />
            <strong>Confiança:</strong> {signal.confiança}%
          </p>
        </div>
      )}
    </div>
  );
}
