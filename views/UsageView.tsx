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
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white p-8 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center">
                    <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mb-4">
                        <BarChart3 size={32} />
                    </div>
                    <div className="text-3xl font-black text-gray-900">
                        {usage?.total_tokens?.toLocaleString() || 0}
                    </div>
                    <h4 className="text-lg font-bold text-gray-800">Tokens Consumidos</h4>
                    <p className="text-sm text-gray-500 mt-1">Total acumulado de tokens LLM (Llama 3.3)</p>
                </div>
                <div className="bg-white p-8 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center">
                    <div className="w-16 h-16 bg-purple-50 text-purple-600 rounded-full flex items-center justify-center mb-4">
                        <Volume2 size={32} />
                    </div>
                    <div className="text-3xl font-black text-gray-900">
                        {usage?.total_minutes?.toLocaleString() || 0}
                    </div>
                    <h4 className="text-lg font-bold text-gray-800">Minutos Generados</h4>
                    <p className="text-sm text-gray-500 mt-1">Tiempo total de interacción de voz (TTS/STT)</p>
                </div>
            </div>

            {/* Live Quota Status */}
            {liveLimits && (
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm animate-in fade-in slide-in-from-bottom-2">
                    <h3 className="text-lg font-bold text-gray-800 mb-6 flex items-center gap-2">
                        <Zap size={20} className="text-yellow-500" />
                        Capacidades y Límites en Tiempo Real
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {liveLimits.groq && liveLimits.groq.active && (
                            <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <img src="https://groq.com/favicon.ico" className="w-5 h-5 rounded" />
                                        <span className="font-bold text-gray-900">Groq Cloud</span>
                                    </div>
                                    <span className="text-[10px] bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-bold uppercase">Live</span>
                                </div>
                                <div className="space-y-3">
                                    <div className="flex justify-between items-center">
                                        <span className="text-xs text-gray-500">Tokens Restantes:</span>
                                        <span className="text-sm font-mono font-bold text-blue-600">
                                            {Number(liveLimits.groq.tokens_remaining).toLocaleString()} / {Number(liveLimits.groq.tokens_limit).toLocaleString()}
                                        </span>
                                    </div>
                                    <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                                        <div
                                            className="bg-blue-600 h-1.5 transition-all duration-1000"
                                            style={{ width: `${(Number(liveLimits.groq.tokens_remaining) / Number(liveLimits.groq.tokens_limit)) * 100}%` }}
                                        ></div>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-xs text-gray-500">Peticiones Restantes:</span>
                                        <span className="text-sm font-mono font-bold text-gray-700">{liveLimits.groq.requests_remaining}</span>
                                    </div>
                                    <div className="text-[10px] text-gray-400 mt-2 italic text-right">
                                        Reset en: {liveLimits.groq.reset_tokens}
                                    </div>
                                </div>
                            </div>
                        )}

                        {liveLimits.google && liveLimits.google.active && (
                            <div className="p-4 rounded-xl bg-gray-50 border border-gray-100">
                                <div className="flex items-center justify-between mb-4">
                                    <div className="flex items-center gap-2">
                                        <span className="w-5 h-5 bg-blue-500 rounded flex items-center justify-center text-[10px] text-white font-bold">G</span>
                                        <span className="font-bold text-gray-900">Google Gemini</span>
                                    </div>
                                    <span className="text-[10px] bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-bold uppercase">Live</span>
                                </div>
                                <div className="space-y-2">
                                    <div className="text-sm text-gray-700 font-medium">{liveLimits.google.info}</div>
                                    <div className="text-xs text-gray-500">Modelo: {liveLimits.google.model}</div>
                                    <div className="mt-4 p-2 bg-blue-50 rounded border border-blue-100 flex items-center gap-2">
                                        <AlertTriangle size={14} className="text-blue-400" />
                                        <span className="text-[10px] text-blue-600">El Tier Standard de Gemini actualiza cuotas por minuto.</span>
                                    </div>
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
                            <a href="https://console.groq.com/settings/limits" target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2 transition-colors">
                                <img src="https://groq.com/favicon.ico" className="w-4 h-4 rounded-sm" onError={(e) => e.currentTarget.src = ''} />
                                Groq Limits
                            </a>
                            <a href="https://aistudio.google.com/app/plan_information" target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-50 flex items-center gap-2 transition-colors">
                                <span className="w-4 h-4 bg-blue-500 rounded-full flex items-center justify-center text-[8px] text-white font-bold">G</span>
                                Google AI Quota
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
