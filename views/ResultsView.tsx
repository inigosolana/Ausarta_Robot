
import React, { useEffect, useState } from 'react';
import { Download, Search, RefreshCw, FileText } from 'lucide-react';

interface SurveyResult {
    id: number;
    telefono: string;
    campaign_name?: string;
    fecha: string;
    completada: number;
    status: string | null;
    puntuacion_comercial: number | null;
    puntuacion_instalador: number | null;
    puntuacion_rapidez: number | null;
    comentarios: string | null;
    transcription: string | null;
    llm_model: string | null;
}

const ResultsView: React.FC = () => {
    const [results, setResults] = useState<SurveyResult[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [viewingTranscript, setViewingTranscript] = useState<SurveyResult | null>(null);

    const loadResults = async () => {
        setLoading(true);
        try {
            const API_URL = import.meta.env.VITE_API_URL || window.location.origin;
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
        (r.campaign_name && r.campaign_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (r.comentarios && r.comentarios.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (r.transcription && r.transcription.toLowerCase().includes(searchTerm.toLowerCase()))
    );

    const exportCSV = () => {
        const headers = ["ID", "Teléfono", "Fecha", "Completada", "Modelo LLM", "P. Comercial", "P. Instalador", "P. Rapidez", "Comentarios", "Transcripción"];
        const csvContent = [
            headers.join(","),
            ...results.map(r => [
                r.id,
                r.telefono,
                new Date(r.fecha).toLocaleString(),
                r.completada ? "Sí" : "No",
                r.llm_model || "Groq",
                r.puntuacion_comercial || "",
                r.puntuacion_instalador || "",
                r.puntuacion_rapidez || "",
                `"${(r.comentarios || "").replace(/"/g, '""')}"`,
                `"${(r.transcription || "").replace(/"/g, '""')}"`
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
                        placeholder="Search by phone, comments or transcript..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-black/5 focus:border-black/20"
                    />
                </div>
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left text-gray-700">
                        <thead className="bg-gray-50 text-gray-500 font-medium border-b border-gray-100">
                            <tr>
                                <th className="px-6 py-3 w-16">ID</th>
                                <th className="px-6 py-3">Phone / Campaign</th>
                                <th className="px-6 py-3">Date</th>
                                <th className="px-6 py-3 text-center">Status</th>
                                <th className="px-6 py-3 text-center">Scores (C/I/R)</th>
                                <th className="px-6 py-3">Model</th>
                                <th className="px-6 py-3">Comments</th>
                                <th className="px-6 py-3 text-right">More</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {filteredResults.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                                        No results found
                                    </td>
                                </tr>
                            ) : filteredResults.map((row) => (
                                <tr key={row.id} className="hover:bg-gray-50/50 transition-colors">
                                    <td className="px-6 py-4 font-mono text-xs text-gray-400">#{row.id}</td>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <span className="font-medium text-gray-900">{row.telefono}</span>
                                            <span className="text-[10px] text-blue-600 font-bold uppercase tracking-tighter">{row.campaign_name}</span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-gray-500">
                                        {new Date(row.fecha).toLocaleDateString()} <span className="text-xs text-gray-400">{new Date(row.fecha).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        {(() => {
                                            if (row.status === 'completed') {
                                                return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-bold bg-green-500 text-white uppercase shadow-sm">Completa</span>;
                                            } else if (row.status === 'incomplete') {
                                                return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-bold bg-blue-400 text-white uppercase shadow-sm">Incompleta</span>;
                                            } else if (row.status === 'rejected_opt_out') {
                                                return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-bold bg-red-500 text-white uppercase shadow-sm" title="Rechazada por Cliente">Rechazada Cliente</span>;
                                            } else if (row.status === 'failed') {
                                                return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-bold bg-orange-400 text-white uppercase shadow-sm">Fallida</span>;
                                            } else {
                                                return <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-bold bg-gray-400 text-white uppercase shadow-sm">Pendiente</span>;
                                            }
                                        })()}
                                    </td>
                                    <td className="px-6 py-4 text-center">
                                        <div className="flex items-center justify-center gap-2">
                                            {[
                                                { label: 'COM', val: row.puntuacion_comercial },
                                                { label: 'INS', val: row.puntuacion_instalador },
                                                { label: 'RAP', val: row.puntuacion_rapidez }
                                            ].map((s, idx) => (
                                                <div key={idx} className="flex flex-col items-center">
                                                    <span className="text-[10px] text-gray-400 mb-0.5">{s.label}</span>
                                                    <span className={`w-8 h-8 flex items-center justify-center rounded-lg text-sm font-bold shadow-sm ${getScoreColor(s.val)}`}>
                                                        {s.val ?? '-'}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex flex-col">
                                            <span className="text-[10px] text-gray-400 font-mono tracking-tighter uppercase whitespace-nowrap">
                                                {row.llm_model?.split(' ')[0] || 'Primary'}
                                            </span>
                                            <span className="text-xs font-semibold text-gray-700">
                                                {row.llm_model?.replace('Google ', '').replace('Groq ', '') || 'Llama 3.3'}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4">
                                        {row.comentarios && row.comentarios !== "Sin comentarios" ? (
                                            <div className="bg-yellow-50 border border-yellow-100 p-2 rounded-lg text-xs text-gray-800 italic max-w-xs truncate">
                                                "{row.comentarios}"
                                            </div>
                                        ) : (
                                            <span className="text-gray-300 italic text-xs">None</span>
                                        )}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <button
                                            onClick={() => setViewingTranscript(row)}
                                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors flex items-center gap-1 text-xs ml-auto"
                                        >
                                            <FileText size={16} /> Transcription
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Transcript Modal */}
            {viewingTranscript && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
                    <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[80vh] flex flex-col overflow-hidden animate-in fade-in zoom-in duration-200">
                        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                            <div>
                                <h3 className="text-lg font-bold text-gray-900">Transcription #{viewingTranscript.id}</h3>
                                <p className="text-xs text-gray-500">{viewingTranscript.telefono} • {new Date(viewingTranscript.fecha).toLocaleString()}</p>
                            </div>
                            <button
                                onClick={() => setViewingTranscript(null)}
                                className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-gray-900 bg-white border border-gray-200 rounded-full hover:shadow-sm transition-all"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto space-y-4 bg-gray-50/20">
                            {viewingTranscript.transcription ? (
                                viewingTranscript.transcription.split('\n').filter(l => l.trim()).map((line, i) => {
                                    const isAgente = line.startsWith('Agente:');
                                    return (
                                        <div key={i} className={`flex ${isAgente ? 'justify-start' : 'justify-end'}`}>
                                            <div className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm shadow-sm border ${isAgente
                                                ? 'bg-blue-600 text-white border-blue-700 rounded-tl-none'
                                                : 'bg-white text-gray-800 border-gray-100 rounded-tr-none'
                                                }`}>
                                                <p className="font-semibold text-[10px] uppercase tracking-wider mb-1 opacity-70">
                                                    {isAgente ? 'Ausarta Robot' : 'Cliente'}
                                                </p>
                                                <p className="leading-relaxed">
                                                    {line.replace(/^(Agente|Cliente): /, '')}
                                                </p>
                                            </div>
                                        </div>
                                    );
                                })
                            ) : (
                                <div className="text-center py-12">
                                    <div className="bg-gray-100 w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3">
                                        <FileText className="text-gray-400" />
                                    </div>
                                    <p className="text-gray-500 font-medium">No transcription available</p>
                                    <p className="text-xs text-gray-400">The call might have been too short or no speech detected.</p>
                                </div>
                            )}
                        </div>

                        <div className="px-6 py-4 border-t border-gray-100 bg-gray-50/50 flex justify-end">
                            <button
                                onClick={() => setViewingTranscript(null)}
                                className="px-6 py-2 bg-gray-900 text-white text-sm font-semibold rounded-xl hover:bg-black transition-all shadow-lg"
                            >
                                Close View
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

function getScoreColor(score: number | null): string {
    if (score === null) return 'bg-gray-50 text-gray-400 border border-gray-100';
    if (score >= 9) return 'bg-green-100 text-green-700 border border-green-200';
    if (score >= 7) return 'bg-blue-100 text-blue-700 border border-blue-200';
    if (score >= 5) return 'bg-yellow-100 text-yellow-700 border border-yellow-200';
    return 'bg-red-100 text-red-700 border border-red-200';
}

export default ResultsView;
