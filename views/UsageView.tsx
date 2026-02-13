import React, { useState, useEffect } from 'react';
import { BarChart3, Globe, Cpu, Mic, Volume2, AlertTriangle, XCircle, Zap } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || window.location.origin + '/api' || 'http://localhost:8002/api';

const UsageView: React.FC = () => {
    const [integrations, setIntegrations] = useState<any[]>([]);
    const [usage, setUsage] = useState<any>(null);
    const [alerts, setAlerts] = useState<any[]>([]);
    const [liveLimits, setLiveLimits] = useState<any>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setIsLoading(true);
            const [intRes, usageRes, limitsRes] = await Promise.all([
                fetch(`${API_URL}/dashboard/integrations`),
                fetch(`${API_URL}/dashboard/usage-stats`),
                fetch(`${API_URL}/ai/limits`)
            ]);

            if (intRes.ok) setIntegrations(await intRes.json());
            if (usageRes.ok) setUsage(await usageRes.json());
            if (limitsRes.ok) setLiveLimits(await limitsRes.json());

            // Fetch alerts specifically for this view too (or pass from props, but independent fetch is fine)
            const alertsRes = await fetch(`${API_URL}/alerts`);
            if (alertsRes.ok) setAlerts(await alertsRes.json());

        } catch (error) {
            console.error('Error loading usage data:', error);
        } finally {
            setIsLoading(false);
        }
    };

    if (isLoading) return <div className="p-8 text-center text-gray-500">Cargando datos de uso...</div>;

    return (
        <div className="space-y-8 animate-fade-in">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3">
                    <BarChart3 className="text-blue-600" size={32} />
                    <h2 className="text-3xl font-bold text-gray-900">Uso y APIs</h2>
                </div>
                <p className="text-gray-500 mt-1">Monitorización de servicios externos y consumo real</p>
            </div>

            {/* API Status Section */}
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                <h3 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
                    <Globe size={20} className="text-blue-500" />
                    Estado de Integraciones
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {integrations.map((int, i) => (
                        <div key={i} className="p-5 rounded-xl border border-gray-100 bg-[#f9fafb] hover:shadow-md transition-shadow">
                            <div className="flex justify-between items-start mb-4">
                                <div className={`p-2 rounded-lg ${int.active ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                                    {int.name.includes('LLM') && <Cpu size={20} />}
                                    {int.name.includes('TTS') && <Volume2 size={20} />}
                                    {int.name.includes('STT') && <Mic size={20} />}
                                    {int.name.includes('LiveKit') && <Globe size={20} />}
                                </div>
                                <span className="flex items-center gap-1.5">
                                    <span className={`w-2.5 h-2.5 rounded-full ${int.active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
                                    <span className={`text-[10px] font-bold uppercase ${int.active ? 'text-green-600' : 'text-red-600'}`}>
                                        {int.active ? 'Online' : 'Offline'}
                                    </span>
                                </span>
                            </div>
                            <div className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">{int.name}</div>
                            <div className="text-xl font-bold text-gray-900">{int.provider}</div>
                            <div className="text-sm text-gray-500 mt-2 font-mono bg-white px-2 py-1 rounded border border-gray-50 truncate">
                                {int.model || int.url || 'API Activa'}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Real usage metrics */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center">
                    <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-3">
                        <BarChart3 size={24} />
                    </div>
                    <div className="text-2xl font-black text-gray-900">
                        {usage?.total_tokens?.toLocaleString() || 0}
                    </div>
                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Total Tokens</h4>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center">
                    <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-full flex items-center justify-center mb-3">
                        <Volume2 size={24} />
                    </div>
                    <div className="text-2xl font-black text-gray-900">
                        {usage?.total_minutes?.toLocaleString() || 0}
                    </div>
                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Minutos Totales</h4>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center">
                    <div className="w-12 h-12 bg-orange-50 text-orange-600 rounded-full flex items-center justify-center mb-3">
                        <Zap size={24} />
                    </div>
                    <div className="text-2xl font-black text-gray-900">
                        {usage?.per_model_stats?.length || 0}
                    </div>
                    <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Modelos Usados</h4>
                </div>
            </div>

            {/* Breakdown per Model Table */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                    <h3 className="text-sm font-bold text-gray-800 flex items-center gap-2">
                        <Cpu size={16} className="text-blue-500" />
                        DESGLOSE DE CONSUMO POR MODELO
                    </h3>
                </div>
                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-white text-[10px] font-black text-gray-400 uppercase tracking-widest border-b border-gray-50">
                                <th className="px-6 py-3">Modelo / Motor</th>
                                <th className="px-6 py-3">Llamadas</th>
                                <th className="px-6 py-3">Tokens Totales</th>
                                <th className="px-6 py-3">Tiempo (Min)</th>
                                <th className="px-6 py-3">Eficiencia (T/min)</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                            {usage?.per_model_stats?.map((stat: any, idx: number) => (
                                <tr key={idx} className="hover:bg-gray-50/50 transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-2">
                                            <div className={`w-2 h-2 rounded-full ${stat.llm_model.includes('Google') ? 'bg-blue-400' :
                                                stat.llm_model.includes('Groq') ? 'bg-orange-400' :
                                                    stat.llm_model.includes('DeepSeek') ? 'bg-blue-700' :
                                                        'bg-green-400'
                                                }`}></div>
                                            <span className="text-sm font-bold text-gray-900">{stat.llm_model}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-sm text-gray-600 font-mono">{stat.calls}</td>
                                    <td className="px-6 py-4 text-sm font-bold text-blue-600 font-mono">{stat.tokens.toLocaleString()}</td>
                                    <td className="px-6 py-4 text-sm text-gray-600 font-mono">{Math.round(stat.seconds / 60)} min</td>
                                    <td className="px-6 py-4 text-sm text-gray-400 font-mono">
                                        {stat.seconds > 0 ? Math.round(stat.tokens / (stat.seconds / 60)) : 0}
                                    </td>
                                </tr>
                            ))}
                            {(!usage?.per_model_stats || usage.per_model_stats.length === 0) && (
                                <tr>
                                    <td colSpan={5} className="px-6 py-8 text-center text-gray-400 text-sm italic">
                                        No hay datos de consumo detallados todavía.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Live Quota Status */}
            {liveLimits && (
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm animate-in fade-in slide-in-from-bottom-2">
                    <h3 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
                        <Zap size={20} className="text-yellow-500" />
                        Capacidades y Límites en Tiempo Real
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {/* Groq Card with Model Selector */}
                        {liveLimits.groq_models && (
                            <div className="lg:col-span-2 p-5 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <img src="https://groq.com/favicon.ico" className="w-5 h-5 rounded" />
                                        <span className="font-bold text-gray-900 uppercase text-xs tracking-wider">Groq Quotas Per Model</span>
                                    </div>
                                    <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-bold">Live</span>
                                </div>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    {Object.entries(liveLimits.groq_models).map(([model, data]: [string, any]) => (
                                        <div key={model} className="bg-white p-3 rounded-lg border border-gray-100 shadow-sm">
                                            <div className="text-[10px] font-bold text-gray-400 truncate mb-2">{model}</div>
                                            <div className="space-y-2">
                                                <div className="flex justify-between text-[11px]">
                                                    <span className="text-gray-500 font-bold">Tokens (TPM):</span>
                                                    <span className="font-mono">
                                                        <span className="font-bold text-blue-600">{Number(data.tokens_remaining).toLocaleString()}</span>
                                                        <span className="text-[10px] text-gray-400"> / {data.tokens_limit ? Number(data.tokens_limit).toLocaleString() : 'Limit'}</span>
                                                    </span>
                                                </div>
                                                <div className="w-full bg-gray-100 rounded-full h-1">
                                                    <div
                                                        className="bg-blue-500 h-1 rounded-full transition-all"
                                                        style={{ width: data.tokens_limit ? `${Math.min(100, (data.tokens_remaining / data.tokens_limit) * 100)}%` : '100%' }}
                                                    ></div>
                                                </div>
                                                <div className="flex justify-between text-[11px]">
                                                    <span className="text-gray-500 font-bold">Peticiones (RPM):</span>
                                                    <span className="font-mono">
                                                        <span className="font-bold text-gray-700">{data.requests_remaining}</span>
                                                        <span className="text-[10px] text-gray-400"> / {data.requests_limit || 'Limit'}</span>
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* OpenAI Card */}
                        {liveLimits.openai && liveLimits.openai.active && (
                            <div className="p-5 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <span className="w-5 h-5 bg-black rounded flex items-center justify-center text-[10px] text-white font-bold">O</span>
                                        <span className="font-bold text-gray-900 uppercase text-xs tracking-wider">OpenAI Limits</span>
                                    </div>
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500">Tokens (TPM):</span>
                                        <span className="font-mono">
                                            <span className="font-bold text-green-600">{liveLimits.openai.tokens_remaining ? Number(liveLimits.openai.tokens_remaining).toLocaleString() : '---'}</span>
                                            <span className="text-gray-400"> / {liveLimits.openai.tokens_limit ? Number(liveLimits.openai.tokens_limit).toLocaleString() : 'Limit'}</span>
                                        </span>
                                    </div>
                                    <div className="w-full bg-gray-200 rounded-full h-1">
                                        <div
                                            className="bg-green-500 h-1 rounded-full transition-all"
                                            style={{ width: liveLimits.openai.tokens_limit ? `${(liveLimits.openai.tokens_remaining / liveLimits.openai.tokens_limit) * 100}%` : '100%' }}
                                        ></div>
                                    </div>
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500">Peticiones (RPM):</span>
                                        <span className="font-mono">
                                            <span className="font-bold text-gray-700">{liveLimits.openai.requests_remaining || '---'}</span>
                                            <span className="text-gray-400"> / {liveLimits.openai.requests_limit || 'Limit'}</span>
                                        </span>
                                    </div>
                                    <div className="p-2 bg-green-50 rounded border border-green-100 text-[10px] text-green-700 text-center font-medium">
                                        {liveLimits.openai.info}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* DeepSeek Card */}
                        {liveLimits.deepseek && liveLimits.deepseek.active && (
                            <div className="p-5 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <div className="w-5 h-5 bg-blue-600 rounded flex items-center justify-center text-[10px] text-white font-bold">DS</div>
                                        <span className="font-bold text-gray-900 uppercase text-xs tracking-wider">DeepSeek Limits</span>
                                    </div>
                                    <span className="text-[10px] bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-bold">V3 / R1</span>
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500">Tokens (TPM):</span>
                                        <span className="font-mono">
                                            <span className="font-bold text-blue-600">{liveLimits.deepseek.tokens_remaining ? Number(liveLimits.deepseek.tokens_remaining).toLocaleString() : '---'}</span>
                                            <span className="text-gray-400"> / {liveLimits.deepseek.tokens_limit ? Number(liveLimits.deepseek.tokens_limit).toLocaleString() : 'Limit'}</span>
                                        </span>
                                    </div>
                                    <div className="w-full bg-gray-200 rounded-full h-1">
                                        <div
                                            className="bg-blue-500 h-1 rounded-full transition-all"
                                            style={{ width: liveLimits.deepseek.tokens_limit ? `${(liveLimits.deepseek.tokens_remaining / liveLimits.deepseek.tokens_limit) * 100}%` : '100%' }}
                                        ></div>
                                    </div>
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500">Peticiones (RPM):</span>
                                        <span className="font-mono">
                                            <span className="font-bold text-gray-700">{liveLimits.deepseek.requests_remaining || '---'}</span>
                                            <span className="text-gray-400"> / {liveLimits.deepseek.requests_limit || 'Limit'}</span>
                                        </span>
                                    </div>
                                    <div className="p-2 bg-blue-50 rounded border border-blue-100 text-[10px] text-blue-700 text-center font-medium">
                                        {liveLimits.deepseek.info}
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Deepgram Card */}
                        {liveLimits.deepgram && (
                            <div className="p-5 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <Mic size={16} className="text-red-500" />
                                        <span className="font-bold text-gray-900 uppercase text-xs tracking-wider">Deepgram Balance</span>
                                    </div>
                                </div>
                                <div className="space-y-4">
                                    {liveLimits.deepgram.balances?.map((b: any, i: number) => (
                                        <div key={i} className="flex flex-col gap-1">
                                            <div className="text-[10px] text-gray-400 font-bold uppercase tracking-widest">
                                                {b.units === 'USD' ? 'Créditos Disponibles' : 'Balance'}
                                            </div>
                                            <div className="text-3xl font-black text-gray-900">
                                                {b.units === 'USD' ? `$${Number(b.amount).toFixed(2)}` : `${b.amount} ${b.units}`}
                                            </div>
                                        </div>
                                    ))}
                                    <div className="text-[10px] text-gray-500 italic bg-white p-2 rounded border border-gray-100">
                                        Este saldo se usa para transcripción en tiempo real (STT).
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* ElevenLabs Card */}
                        {liveLimits.elevenlabs && liveLimits.elevenlabs.active && (
                            <div className="p-5 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <Volume2 size={16} className="text-purple-600" />
                                        <span className="font-bold text-gray-900 uppercase text-xs tracking-wider">ElevenLabs</span>
                                    </div>
                                    <span className="text-[10px] bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-bold">Characters</span>
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500">Sobrantes:</span>
                                        <span className="font-mono font-bold text-purple-600">
                                            {Number(liveLimits.elevenlabs.characters_remaining).toLocaleString()}
                                        </span>
                                    </div>
                                    <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                                        <div
                                            className="bg-purple-600 h-1.5 transition-all"
                                            style={{ width: `${(liveLimits.elevenlabs.characters_remaining / liveLimits.elevenlabs.characters_limit) * 100}%` }}
                                        ></div>
                                    </div>
                                    <div className="text-[10px] text-gray-400 text-center font-medium italic">
                                        Total: {Number(liveLimits.elevenlabs.characters_limit / 1000).toLocaleString()}k chars
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Cartesia Card */}
                        {liveLimits.cartesia && liveLimits.cartesia.active && (
                            <div className="p-5 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <div className="w-5 h-5 bg-purple-500 rounded flex items-center justify-center text-[10px] text-white font-bold">C</div>
                                        <span className="font-bold text-gray-900 uppercase text-xs tracking-wider">Cartesia TTS</span>
                                    </div>
                                </div>
                                <div className="space-y-3">
                                    <div className="text-xs text-gray-700 font-medium">
                                        {liveLimits.cartesia.info}
                                    </div>
                                    <a
                                        href={liveLimits.cartesia.dashboard_url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="block w-full text-center py-2 bg-white border border-purple-200 text-[10px] text-purple-600 font-bold rounded hover:bg-purple-50 transition-colors uppercase"
                                    >
                                        Ver Saldo Cartesia
                                    </a>
                                </div>
                            </div>
                        )}

                        {/* Google Card */}
                        {liveLimits.google && liveLimits.google.active && (
                            <div className="p-5 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <span className="w-5 h-5 bg-blue-500 rounded flex items-center justify-center text-[10px] text-white font-bold">G</span>
                                        <span className="font-bold text-gray-900 uppercase text-xs tracking-wider">Google Gemini</span>
                                    </div>
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between items-center text-xs">
                                        <span className="text-gray-500 font-bold">Capacidad estimada:</span>
                                    </div>
                                    <div className="p-3 bg-blue-50 rounded border border-blue-100 space-y-2">
                                        <div className="flex justify-between text-[11px]">
                                            <span className="text-blue-700">Tokens (TPM):</span>
                                            <span className="font-bold text-blue-800">1,000,000</span>
                                        </div>
                                        <div className="flex justify-between text-[11px]">
                                            <span className="text-blue-700">Peticiones (RPM):</span>
                                            <span className="font-bold text-blue-800">15</span>
                                        </div>
                                    </div>
                                    <div className="text-[10px] text-gray-500 italic">Google no expone límites live vía API simple, se usan valores de Tier Standard.</div>
                                    <button
                                        onClick={async () => {
                                            const res = await fetch(`${API_URL}/ai/diagnose-google`);
                                            const data = await res.json();
                                            if (data.status === 'success') alert("Modelos: " + data.available_models.join(", "));
                                        }}
                                        className="w-full py-2 border border-blue-200 text-[10px] text-blue-600 font-bold rounded hover:bg-blue-50 transition-colors uppercase"
                                    >
                                        Diagnostar Modelos
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Provider Dashboards Link (For Remaining Quota) */}
            <div className="bg-blue-50 p-6 rounded-xl border border-blue-100 shadow-sm">
                <div className="flex items-start gap-4">
                    <div className="bg-blue-100 p-3 rounded-full text-blue-600">
                        <Cpu size={24} />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900">Check Remaining Quota & Limits</h3>
                        <p className="text-sm text-gray-600 mb-4">
                            The metrics above show usage consumed by this agent. To see your exact remaining balance, credits, or rate limits, please visit your provider's dashboard:
                        </p>
                        <div className="flex flex-wrap gap-3">
                            <a href="https://platform.openai.com/usage" target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2 transition-colors">
                                <span className="w-4 h-4 bg-black rounded-full flex items-center justify-center text-[8px] text-white font-bold">O</span>
                                OpenAI Usage
                            </a>
                            <a href="https://console.groq.com/settings/limits" target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2 transition-colors">
                                <img src="https://groq.com/favicon.ico" className="w-4 h-4 rounded-sm" onError={(e) => e.currentTarget.src = ''} />
                                Groq Limits
                            </a>
                            <a href="https://aistudio.google.com/app/plan_information" target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2 transition-colors">
                                <span className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center text-[8px] text-white font-bold">G</span>
                                Google AI Quota
                            </a>
                            <a href="https://platform.deepseek.com/usage" target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2 transition-colors">
                                <span className="w-4 h-4 bg-blue-600 rounded-full flex items-center justify-center text-[8px] text-white font-bold">DS</span>
                                DeepSeek Usage
                            </a>
                            <a href="https://play.cartesia.ai/settings" target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2 transition-colors">
                                <span className="w-4 h-4 bg-purple-500 rounded-full flex items-center justify-center text-[8px] text-white font-bold">C</span>
                                Cartesia Credits
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            {/* System Alerts Log */}
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                <h3 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
                    <AlertTriangle size={20} className="text-orange-500" />
                    Registro de Alertas y Límites
                </h3>
                {alerts.length === 0 ? (
                    <p className="text-gray-500 text-sm">No hay alertas activas en el sistema.</p>
                ) : (
                    <div className="space-y-3">
                        {alerts.map((alert) => (
                            <div key={alert.id} className="border-l-4 border-red-500 bg-red-50 p-4 rounded-r-lg flex justify-between items-start">
                                <div>
                                    <div className="flex items-center gap-2 mb-1">
                                        <XCircle size={16} className="text-red-500" />
                                        <span className="font-bold text-red-800 uppercase text-xs tracking-wider">{alert.type}</span>
                                        <span className="text-xs text-red-400">
                                            {new Date(alert.created_at + (alert.created_at.endsWith('Z') ? '' : 'Z')).toLocaleString()}
                                        </span>
                                    </div>
                                    <p className="text-sm text-red-700 font-medium">{alert.message}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default UsageView;
