import React, { useState, useEffect } from 'react';
import {
    Phone,
    CheckCircle,
    BarChart2,
    Timer,
    User,
    Calendar
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
    date: string;
    status: string;
    scores: {
        comercial: number | null;
        instalador: number | null;
        rapidez: number | null;
    };
}

const DashboardView: React.FC = () => {
    const [stats, setStats] = useState<DashboardStats | null>(null);
    const [recentCalls, setRecentCalls] = useState<Call[]>([]);
    const [integrations, setIntegrations] = useState<any[]>([]);
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

            {/* API Integrations usage section requested by user */}
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
                <h3 className="text-lg font-bold text-gray-800 mb-4">APIs en Uso (Status)</h3>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {integrations.map((int, i) => (
                        <div key={i} className="p-4 rounded-lg border border-gray-50 bg-gray-50/50">
                            <div className="flex justify-between items-start mb-2">
                                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">{int.name}</span>
                                <span className={`w-2 h-2 rounded-full ${int.active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
                            </div>
                            <div className="font-bold text-gray-900">{int.provider}</div>
                            <div className="text-xs text-gray-500 mt-1 truncate">
                                {int.model || int.url || 'Configurado'}
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <h3 className="text-lg font-bold text-gray-800 mb-4">Últimas Llamadas</h3>
                <div className="overflow-y-auto max-h-[200px]">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Teléfono</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fecha</th>
                                <th className="px-3 py-2 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">C / I / R</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Estado</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {recentCalls.map((call) => (
                                <tr key={call.id}>
                                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 flex items-center gap-2">
                                        <User size={14} className="text-gray-400" />
                                        {call.phone}
                                    </td>
                                    <td className="px-3 py-2 whitespace-nowrap text-xs text-gray-500">
                                        {new Date(call.date).toLocaleString()}
                                    </td>
                                    <td className="px-3 py-2 whitespace-nowrap text-sm text-center font-mono font-bold text-gray-700">
                                        {call.scores?.comercial ?? '-'} / {call.scores?.instalador ?? '-'} / {call.scores?.rapidez ?? '-'}
                                    </td>
                                    <td className="px-3 py-2 whitespace-nowrap text-sm">
                                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${call.status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                                            }`}>
                                            {call.status === 'completed' ? 'Completada' : 'Pendiente'}
                                        </span>
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
