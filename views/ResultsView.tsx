
import React, { useEffect, useState } from 'react';
import { Download, Search, RefreshCw, FileText } from 'lucide-react';

interface SurveyResult {
    id: number;
    telefono: string;
    fecha: string;
    completada: number;
    puntuacion_comercial: number | null;
    puntuacion_instalador: number | null;
    puntuacion_rapidez: number | null;
    comentarios: string | null;
}

const ResultsView: React.FC = () => {
    const [results, setResults] = useState<SurveyResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    const loadResults = async () => {
        setLoading(true);
        try {
            const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002';
            const res = await fetch(`${API_URL}/api/results`);
            if (res.ok) {
                const data = await res.json();
                setResults(data);
            }
        } catch (e) {
            console.error("Error loading results", e);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadResults();
    }, []);

    const filteredResults = results.filter(r =>
        r.telefono.includes(searchTerm) ||
        (r.comentarios && r.comentarios.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    const exportCSV = () => {
        const headers = ["ID", "Teléfono", "Fecha", "Completada", "P. Comercial", "P. Instalador", "P. Rapidez", "Comentarios"];
        const csvContent = [
            headers.join(","),
            ...results.map(r => [
                r.id,
                r.telefono,
                new Date(r.fecha).toLocaleString(),
                r.completada ? "Sí" : "No",
                r.puntuacion_comercial || "",
                r.puntuacion_instalador || "",
                r.puntuacion_rapidez || "",
                `"${(r.comentarios || "").replace(/"/g, '""')}"`
            ].join(","))
        ].join("\n");

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", "encuestas_ausarta.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    return (
        <div className="space-y-6">
            <header className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Survey Results</h1>
                    <p className="text-gray-500 text-sm mt-1">Detailed view of all agent interactions</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={loadResults}
                        className="p-2 bg-white border border-gray-200 text-gray-600 rounded-lg hover:bg-gray-50 transition-colors"
                    >
                        <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
                    </button>
                    <button
                        onClick={exportCSV}
                        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition-colors"
                    >
                        <Download size={16} />
                        Export CSV
                    </button>
                </div>
            </header>

            {/* Filters */}
            <div className="flex gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
                    <input
                        type="text"
                        placeholder="Search by phone or comments..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black/20"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-gray-50 text-gray-500 font-medium border-b border-gray-100">
                            <tr>
                                <th className="px-6 py-3 w-16">ID</th>
                                <th className="px-6 py-3">Phone</th>
                                <th className="px-6 py-3">Date</th>
                                <th className="px-6 py-3 text-center">Status</th>
                                <th className="px-6 py-3 text-center">Scores (C/I/R)</th>
                                <th className="px-6 py-3">Comments</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {filteredResults.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-12 text-center text-gray-400">
                                        No results found
                                    </td>
                                </tr>
                            ) : filteredResults.map((row) => (
                                <tr key={row.id} className="hover:bg-gray-50/50 transition-colors">
                                    <td className="px-6 py-4 font-mono text-xs text-gray-400">#{row.id}</td>
                                    <td className="px-6 py-4 font-medium text-gray-900">{row.telefono}</td>
                                    <td className="px-6 py-4 text-gray-500">
                                        {new Date(row.fecha).toLocaleDateString()} <span className="text-xs text-gray-400">{new Date(row.fecha).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        {row.completada ? (
                                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-100">
                                                Completed
                                            </span>
                                        ) : (
                                            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-50 text-yellow-700 border border-yellow-100">
                                                Partial / Incomplete
                                            </span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <div className="flex items-center justify-center gap-2">
                                            <div className="flex flex-col items-center">
                                                <span className="text-[10px] text-gray-400 mb-0.5">COM</span>
                                                <span className={`w-8 h-8 flex items-center justify-center rounded-lg text-sm font-bold shadow-sm ${getScoreColor(row.puntuacion_comercial)}`}>
                                                    {row.puntuacion_comercial ?? '-'}
                                                </span>
                                            </div>
                                            <div className="flex flex-col items-center">
                                                <span className="text-[10px] text-gray-400 mb-0.5">INS</span>
                                                <span className={`w-8 h-8 flex items-center justify-center rounded-lg text-sm font-bold shadow-sm ${getScoreColor(row.puntuacion_instalador)}`}>
                                                    {row.puntuacion_instalador ?? '-'}
                                                </span>
                                            </div>
                                            <div className="flex flex-col items-center">
                                                <span className="text-[10px] text-gray-400 mb-0.5">RAP</span>
                                                <span className={`w-8 h-8 flex items-center justify-center rounded-lg text-sm font-bold shadow-sm ${getScoreColor(row.puntuacion_rapidez)}`}>
                                                    {row.puntuacion_rapidez ?? '-'}
                                                </span>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        {row.comentarios && row.comentarios !== "Sin comentarios" ? (
                                            <div className="bg-yellow-50 border border-yellow-100 p-3 rounded-lg text-sm text-gray-800 italic relative">
                                                <span className="absolute top-2 left-2 text-yellow-300 text-xl leading-none">"</span>
                                                <p className="pl-4 pr-2">{row.comentarios}</p>
                                            </div>
                                        ) : (
                                            <span className="text-gray-300 italic text-xs">No highlighted comments</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

function getScoreColor(score: number | null): string {
    if (score === null) return 'bg-gray-100 text-gray-400';
    if (score >= 9) return 'bg-green-100 text-green-700';
    if (score >= 7) return 'bg-blue-100 text-blue-700';
    if (score >= 5) return 'bg-yellow-100 text-yellow-700';
    return 'bg-red-100 text-red-700';
}

export default ResultsView;
