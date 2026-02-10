import React, { useState, useEffect } from 'react';
import { BarChart3, Globe, Cpu, Mic, Volume2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || window.location.origin + '/api' || 'http://localhost:8002/api';

const UsageView: React.FC = () => {
    const [integrations, setIntegrations] = useState<any[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setIsLoading(true);
            const res = await fetch(`${API_URL}/dashboard/integrations`);
            if (res.ok) setIntegrations(await res.json());
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
                <p className="text-gray-500 mt-1">Monitorización de servicios externos y consumo</p>
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

            {/* Placeholder for future usage metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white p-8 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center opacity-70">
                    <div className="w-16 h-16 bg-blue-50 text-blue-400 rounded-full flex items-center justify-center mb-4">
                        <BarChart3 size={32} />
                    </div>
                    <h4 className="text-lg font-bold text-gray-800">Consumo de Tokens</h4>
                    <p className="text-sm text-gray-500 mt-2">Gráficas de consumo detallado por modelo bajo desarrollo.</p>
                </div>
                <div className="bg-white p-8 rounded-xl border border-gray-100 shadow-sm flex flex-col items-center justify-center text-center opacity-70">
                    <div className="w-16 h-16 bg-purple-50 text-purple-400 rounded-full flex items-center justify-center mb-4">
                        <Volume2 size={32} />
                    </div>
                    <h4 className="text-lg font-bold text-gray-800">Minutos Generados</h4>
                    <p className="text-sm text-gray-500 mt-2">Seguimiento de minutos de voz procesados próximamente.</p>
                </div>
            </div>
        </div>
    );
};

export default UsageView;
