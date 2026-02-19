import React, { useState, useEffect } from 'react';
import {
    Phone,
    CheckCircle,
    BarChart2,
    Timer,
    User,
    Calendar,
    Zap
} from 'lucide-react';

// API URL
const API_URL = import.meta.env.VITE_API_URL || window.location.origin + '/api' || 'http://localhost:8002/api';

interface DashboardStats {
    total_calls: number;
    completed_calls: number;
    pending_calls: number;
    avg_scores: {
        comercial: number;
        instalador: number;
        rapidez: number;
        overall: number;
    };
}

interface Call {
    id: number;
    phone: number;
    campaign: string;
    date: string;
    status: string;
    scores: {
        comercial: number | null;
        instalador: number | null;
        rapidez: number | null;
    };
    llm_model?: string | null;
}

interface Integration {
    name: string;
    provider: string;
    active: boolean;
    model?: string;
    url?: string;
    env_var?: string;
}

const StatCard = ({ title, value, icon: Icon, color }: any) => (
    <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between">
        <div>
            <p className="text-sm font-medium text-gray-500">{title}</p>
            <h3 className="text-3xl font-bold text-gray-800 mt-2">{value}</h3>
        </div>
        <div className={`p-3 rounded-full bg-${color}-50 text-${color}-600`}>
            <Icon size={24} />
        </div>
    </div>
);

const IntegrationCard: React.FC<{ integ: Integration }> = ({ integ }) => (
    <div className={`p-4 rounded-xl border flex items-center justify-between ${integ.active ? 'bg-green-50 border-green-100' : 'bg-red-50 border-red-100'}`}>
        <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${integ.active ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                <Zap size={18} />
            </div>
            <div>
                <h4 className="font-semibold text-gray-900 text-sm">{integ.name}</h4>
                <p className="text-xs text-gray-500">{integ.provider} • {integ.model || 'Cloud'}</p>
                {!integ.active && integ.env_var && (
                    <code className="text-[10px] bg-red-100 text-red-700 px-1 rounded block mt-1 w-fit">
                        Missing: {integ.env_var}
                    </code>
                )}
                {integ.active && integ.env_var && (
                    <code className="text-[10px] bg-green-100 text-green-700 px-1 rounded block mt-1 w-fit">
                        active: {integ.env_var}
                    </code>
                )}
            </div>
        </div>
        <div className={`px-2 py-1 rounded text-xs font-bold uppercase ${integ.active ? 'bg-green-200 text-green-800' : 'bg-red-200 text-red-800'}`}>
            {integ.active ? 'Active' : 'Offline'}
        </div>
    </div>
);

const DashboardView: React.FC = () => {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [recentCalls, setRecentCalls] = useState<Call[]>([]);
    const [integrations, setIntegrations] = useState<Integration[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            setIsLoading(true);
            const [statsRes, callsRes, intRes] = await Promise.all([
                fetch(`${API_URL}/dashboard/stats`),
                fetch(`${API_URL}/dashboard/recent-calls`),
                fetch(`${API_URL}/dashboard/integrations`)
            ]);

            if (statsRes.ok) setStats(await statsRes.json());
            if (callsRes.ok) setRecentCalls(await callsRes.json());
            if (intRes.ok) setIntegrations(await intRes.json());

        } catch (error) {
            console.error('Error loading dashboard data:', error);
        } finally {
            setIsLoading(false);
        }
    };



    if (isLoading) return <div className="p-8 text-center text-gray-500">Cargando dashboard...</div>;

    return (
        <div className="space-y-8 animate-fade-in">
            {/* Header */}
            <div>
                <div className="flex items-center gap-3">
                    <img src="/ausarta.png" alt="Logo" className="h-10 w-auto object-contain" />
                    <h2 className="text-3xl font-bold text-gray-900">Dashboard</h2>
                </div>
                <p className="text-gray-500 mt-1">Resumen de actividad de encuestas</p>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                <StatCard
                    title="Total Llamadas"
                    value={stats?.total_calls || 0}
                    icon={Phone}
                    color="blue"
                />
                <StatCard
                    title="Completadas"
                    value={stats?.completed_calls || 0}
                    icon={CheckCircle}
                    color="green"
                />
                <StatCard
                    title="Nota Media"
                    value={stats?.avg_scores?.overall || 0}
                    icon={BarChart2}
                    color="purple"
                />
                <StatCard
                    title="Fichas Pendientes"
                    value={stats?.pending_calls || 0}
                    icon={Timer}
                    color="yellow"
                />
            </div>

            {/* Integrations Status */}
            <div>
                <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center gap-2">
                    <Zap size={20} className="text-yellow-500" /> Estado de Servicios (APIs)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {integrations.map((intext, i) => (
                        <IntegrationCard key={i} integ={intext} />
                    ))}
                </div>
            </div>

            {/* Scores & Graphs */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                    <h3 className="text-lg font-bold text-gray-800 mb-4">Métricas de Calidad</h3>
                    <div className="space-y-4">
                        <div>
                            <div className="flex justify-between mb-1">
                                <span className="text-sm font-medium text-gray-600">Trato Comercial</span>
                                <span className="text-sm font-bold text-gray-800">{stats?.avg_scores?.comercial || 0}/10</span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-2.5">
                                <div
                                    className="bg-blue-600 h-2.5 rounded-full"
                                    style={{ width: `${(stats?.avg_scores?.comercial || 0) * 10}%` }}
                                ></div>
                            </div>
                        </div>

                        <div>
                            <div className="flex justify-between mb-1">
                                <span className="text-sm font-medium text-gray-600">Instalador</span>
                                <span className="text-sm font-bold text-gray-800">{stats?.avg_scores?.instalador || 0}/10</span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-2.5">
                                <div
                                    className="bg-green-600 h-2.5 rounded-full"
                                    style={{ width: `${(stats?.avg_scores?.instalador || 0) * 10}%` }}
                                ></div>
                            </div>
                        </div>

                        <div>
                            <div className="flex justify-between mb-1">
                                <span className="text-sm font-medium text-gray-600">Rapidez</span>
                                <span className="text-sm font-bold text-gray-800">{stats?.avg_scores?.rapidez || 0}/10</span>
                            </div>
                            <div className="w-full bg-gray-100 rounded-full h-2.5">
                                <div
                                    className="bg-purple-600 h-2.5 rounded-full"
                                    style={{ width: `${(stats?.avg_scores?.rapidez || 0) * 10}%` }}
                                ></div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>

            {/* Recent Activity */}
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <h3 className="text-lg font-bold text-gray-800 mb-4">Últimas Llamadas</h3>
                <div className="overflow-y-auto max-h-[200px]">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Teléfono / Campaña</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
                                <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">C / I / R</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IA / Modelo</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {recentCalls.map((call) => (
                                <tr key={call.id}>
                                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 flex items-center gap-2">
                                        <div className="flex flex-col">
                                            <div className="flex items-center gap-1">
                                                <User size={12} className="text-gray-400" />
                                                <span className="font-medium text-xs">{call.phone}</span>
                                            </div>
                                            <span className="text-[10px] text-blue-600 font-bold uppercase tracking-tighter ml-4">{call.campaign}</span>
                                        </div>
                                    </td>
                                    <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-500">
                                        {new Date(call.date).toLocaleString()}
                                    </td>
                                    <td className="px-3 py-2 whitespace-nowrap text-sm text-center font-mono font-bold text-gray-700">
                                        {call.scores?.comercial ?? '-'} / {call.scores?.instalador ?? '-'} / {call.scores?.rapidez ?? '-'}
                                    </td>
                                    <td className="px-3 py-2 whitespace-nowrap">
                                        <div className="flex flex-col">
                                            <span className="text-[9px] text-gray-400 font-bold uppercase">{call.llm_model?.split(' ')[0] || 'AI'}</span>
                                            <span className="text-[10px] text-gray-600 truncate max-w-[80px]">{(call.llm_model || 'Standard').replace('Groq ', '')}</span>
                                        </div>
                                    </td>
                                    <td className="px-3 py-2 whitespace-nowrap text-sm">
                                        {(() => {
                                            switch (call.status) {
                                                case 'completed':
                                                    return <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-green-500 text-white uppercase shadow-sm">Completa</span>;
                                                case 'incomplete':
                                                    return <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-blue-400 text-white uppercase shadow-sm">Incompleta</span>;
                                                case 'rejected_opt_out':
                                                case 'rejected':
                                                    return <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-red-500 text-white uppercase shadow-sm">Rechazada</span>;
                                                case 'failed':
                                                    return <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-orange-400 text-white uppercase shadow-sm">Fallida</span>;
                                                case 'initiated':
                                                    return <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-yellow-400 text-white uppercase shadow-sm">En Curso</span>;
                                                default:
                                                    return <span className="px-2 py-1 rounded-full text-[10px] font-bold bg-gray-400 text-white uppercase shadow-sm">Pendiente</span>;
                                            }
                                        })()}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    {recentCalls.length === 0 && (
                        <p className="text-center text-gray-400 mt-4 text-sm">No hay llamadas recientes</p>
                    )}
                </div>
            </div>
        </div>
    );
};

export default DashboardView;
