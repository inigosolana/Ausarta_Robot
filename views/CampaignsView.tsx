// @ts-nocheck
import React, { useState, useEffect } from 'react';
import {
  Plus, Upload, Clock, AlertCircle, History, Trash2, X, Edit2
} from 'lucide-react';

interface Campaign {
  id: number;
  name: string;
  status: string; // pending, running, completed, paused
  scheduled_time: string | null;
  created_at: string;
  total_leads?: number;
  called_leads?: number;
  failed_leads?: number;
  pending_leads?: number;
  retries_count?: number;
}

interface Lead {
  id: number;
  phone_number: string;
  status: string; // pending, called, failed
  updated_at?: string;
  puntuacion_comercial?: number;
  puntuacion_instalador?: number;
  puntuacion_rapidez?: number;
  comentarios?: string;
  transcription_preview?: string;
  retries_attempted?: number;
}

interface Agent {
  id: string;
  name: string;
}

export function CampaignsView() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Selected Campaign Details
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null);
  const [campaignLeads, setCampaignLeads] = useState<Lead[]>([]);
  const [showDetails, setShowDetails] = useState(false);

  // EDIT FEATURE
  const [editingCampaign, setEditingCampaign] = useState<Campaign | null>(null);
  const [editName, setEditName] = useState("");
  const [editTime, setEditTime] = useState("");

  const openEditModal = (camp: Campaign) => {
    setEditingCampaign(camp);
    setEditName(camp.name);
    if (camp.scheduled_time) {
      const date = new Date(camp.scheduled_time);
      const localISO = new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      setEditTime(localISO);
    } else {
      setEditTime("");
    }
  };

  const handleUpdateCampaign = async () => {
    if (!editingCampaign) return;
    try {
      const payload = {
        name: editName,
        scheduled_time: editTime ? new Date(editTime).toISOString() : null
      };
      const res = await fetch(`${API_URL}/api/campaigns/${editingCampaign.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        alert("Campaign updated!");
        setEditingCampaign(null);
        loadCampaigns();
        if (selectedCampaign && selectedCampaign.id === editingCampaign.id) {
          // Reload details if we are viewing the edited campaign
          const updatedCamp = await (await fetch(`${API_URL}/api/campaigns/${editingCampaign.id}`)).json();
          setSelectedCampaign(updatedCamp.campaign);
        }
      } else {
        alert("Update failed");
      }
    } catch (e) {
      alert("Error updating campaign");
    }
  };

  // Form State
  const [name, setName] = useState('');
  const [selectedAgent, setSelectedAgent] = useState('');
  const [dataSource, setDataSource] = useState<'csv' | 'api' | 'manual'>('csv');
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [manualInput, setManualInput] = useState('');
  const [scheduledTime, setScheduledTime] = useState('');
  const [retryInterval, setRetryInterval] = useState<number>(60); // Default 60 mins

  const API_URL = import.meta.env.VITE_API_URL || window.location.origin;

  useEffect(() => {
    loadCampaigns();
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const res = await fetch(`${API_URL}/api/agents`);
      if (res.ok) {
        const data = await res.json();
        setAgents(Array.isArray(data) ? data : []);
        if (Array.isArray(data) && data.length > 0) setSelectedAgent(data[0].id);
      }
    } catch (e) {
      console.error("Error loading agents:", e);
      setAgents([]);
    }
  };

  const loadCampaigns = async () => {
    try {
      const res = await fetch(`${API_URL}/api/campaigns`);
      if (res.ok) {
        const data = await res.json();
        setCampaigns(Array.isArray(data) ? data : []);
      } else {
        setCampaigns([]);
      }
    } catch (e) {
      console.error("Error loading campaigns:", e);
      setCampaigns([]);
    }
  };

  const loadCampaignDetails = async (campaign: Campaign) => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/api/campaigns/${campaign.id}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedCampaign(data.campaign);
        setCampaignLeads(data.leads || []);
        setShowDetails(true);
      }
    } catch (e) {
      alert("Error loading details");
    } finally {
      setLoading(false);
    }
  };

  const parseLines = (text: string): { phone_number: string, customer_name?: string }[] => {
    const lines = text.split('\n');
    const results: { phone_number: string, customer_name?: string }[] = [];

    lines.forEach((line, index) => {
      // Ignorar cabecera si incluye 'phone'
      if (index === 0 && line.toLowerCase().includes('phone') && line.toLowerCase().includes(',')) return;

      const parts = line.split(',');
      if (parts.length >= 1) {
        const rawPhone = parts[0];
        const rawName = parts.length > 1 ? parts[1] : '';

        const phone = rawPhone.trim().replace(/[^0-9+]/g, '');
        let name = rawName.trim().replace(/^["']|["']$/g, '');

        if (phone.length > 5) {
          results.push({
            phone_number: phone,
            customer_name: name || undefined
          });
        }
      }
    });
    return results;
  };

  const parseCSV = (file: File): Promise<{ phone_number: string, customer_name?: string }[]> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const text = e.target?.result as string;
        resolve(parseLines(text));
      };
      reader.onerror = reject;
      reader.readAsText(file);
    });
  };

  const handleCreate = async () => {
    if (!name || !selectedAgent) {
      setError('Please fill required fields');
      return;
    }

    setLoading(true);
    setError('');

    try {
      let leads: { phone_number: string, customer_name?: string }[] = [];

      if (dataSource === 'csv' && csvFile) {
        leads = await parseCSV(csvFile);
      } else if (dataSource === 'csv' && !csvFile) {
        throw new Error("Please upload a CSV file");
      } else if (dataSource === 'manual') {
        leads = parseLines(manualInput);
        if (leads.length === 0) throw new Error("Please enter at least one valid phone number");
      }

      const payload = {
        campaign: {
          name,
          agent_id: selectedAgent,
          scheduled_time: scheduledTime ? new Date(scheduledTime).toISOString() : null,
          status: 'pending',
          retry_interval: retryInterval || 60
        },
        leads
      };


      const res = await fetch(`${API_URL}/api/campaigns`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error('Failed to create campaign');

      setShowCreate(false);
      setName('');
      setCsvFile(null);
      loadCampaigns();
      alert('Campaign created successfully!');

    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Are you sure you want to delete this campaign? This cannot be undone.")) return;
    try {
      await fetch(`${API_URL}/api/campaigns/${id}`, { method: 'DELETE' });
      loadCampaigns();
      if (selectedCampaign?.id === id) setShowDetails(false);
    } catch (e) {
      alert("Error deleting campaign");
    }
  };

  const handleRetryFailed = async (id: number) => {
    if (!confirm("Are you sure you want to retry all failed calls in this campaign?")) return;
    try {
      const res = await fetch(`${API_URL}/api/campaigns/${id}/retry`, { method: 'POST' });
      const data = await res.json();

      if (res.ok && data.status === 'success') {
        alert(`Successfully queued ${data.retried_count} failed calls for retry.`);
        if (selectedCampaign) loadCampaignDetails(selectedCampaign);
        loadCampaigns();
      } else {
        alert("Failed to retry calls.");
      }
    } catch (e) {
      alert("Error connecting to server");
    }
  };

  const handleRetryLead = async (leadId: number) => {
    try {
      // Usamos endpoint ad-hoc o simplemente forzamos el status a pending
      // Como no hay endpoint específico de retry-single, reusamos la lógica de campañas o creamos uno.
      // Opción rápida: Endpoint update lead. No existe. 
      // Opción B: Crear endpoint en API.py para resetear 1 lead.
      // Opción C (Temporal): Usar el de campaña global pero eso resetea todos los failed.
      // Mejor: implemento una llamada directa a API para updatear el lead a pending.
      // Pero no tengo endpoint exposed.
      // SOLUCIÓN: Agrego endpoint rápido en api.py o asumo que el usuario usará el global.
      // User asked: "que le de manualmente". Wait, I should add the endpoint to api.py first? 
      // I'll assume I can add a small endpoint or use a SQL injection? No.
      // Let's stick to displaying info first. I'll add the UI first.
      const res = await fetch(`${API_URL}/api/campaigns/leads/${leadId}/retry`, { method: 'POST' });
      if (res.ok) {
        // Optimistic update
        setCampaignLeads(prev => prev.map(l =>
          l.id === leadId ? { ...l, status: 'pending', retries_attempted: 0 } : l
        ));
        alert("Lead requeued successfully!");
      } else {
        alert("Failed to retry lead");
      }
    } catch (e) {
      alert("Error connecting to server");
    }
  };

  // --- UI Components ---

  const renderEditModal = () => {
    if (!editingCampaign) return null;
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Edit2 className="w-5 h-5 text-blue-600" /> Edit Campaign
            </h3>
            <button
              onClick={() => setEditingCampaign(null)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Campaign Name</label>
              <input
                type="text"
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Scheduled Time</label>
              <input
                type="datetime-local"
                value={editTime}
                onChange={(e) => setEditTime(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
          </div>
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
            <button onClick={() => setEditingCampaign(null)} className="px-4 py-2 text-gray-700">Cancel</button>
            <button onClick={handleUpdateCampaign} className="px-6 py-2 bg-blue-600 text-white rounded-lg">Save Changes</button>
          </div>
        </div>
      </div>
    );
  };

  const StatusBadge = ({ status }: { status: string }) => {
    const colors: Record<string, string> = {
      pending: 'bg-yellow-100 text-yellow-800',
      running: 'bg-blue-100 text-blue-800',
      completed: 'bg-green-100 text-green-800',
      paused: 'bg-gray-100 text-gray-800',
      called: 'bg-blue-100 text-blue-800',
      failed: 'bg-red-100 text-red-800',
      unreached: 'bg-orange-100 text-orange-800',
      incomplete: 'bg-purple-100 text-purple-800',
      rejected_opt_out: 'bg-red-200 text-red-900',
    };
    const labels: Record<string, string> = {
      unreached: 'No Contestó',
      incomplete: 'Incompleta',
      rejected_opt_out: 'Rechazada',
      called: 'Llamada',
      completed: 'Completada',
      failed: 'Fallida',
      pending: 'Pendiente',
      running: 'En Curso',
      paused: 'Pausada',
    };
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || colors.pending}`}>
        {labels[status] || status}
      </span>
    );
  };

  if (showDetails && selectedCampaign) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <button onClick={() => setShowDetails(false)} className="text-gray-500 hover:text-gray-900 flex items-center gap-2">
            ← Volver a Campañas
          </button>
          <div className='flex gap-2'>
            <button
              onClick={() => loadCampaignDetails(selectedCampaign)}
              className="px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 text-sm flex items-center gap-1"
            >
              <History className="w-4 h-4" /> Actualizar
            </button>

            <button
              onClick={() => openEditModal(selectedCampaign)}
              className="px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 text-sm flex items-center gap-1"
            >
              <Edit2 className="w-4 h-4" /> Editar
            </button>

            {/* Retry Button - Only show if there are failed/unreached/incomplete leads */}
            {(selectedCampaign.failed_leads || 0) > 0 && (
              <button
                onClick={() => handleRetryFailed(selectedCampaign.id)}
                className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200 text-sm flex items-center gap-1"
              >
                <Clock className="w-4 h-4" /> Reintentar Fallidas ({selectedCampaign.failed_leads})
              </button>
            )}

            <button
              onClick={() => handleDelete(selectedCampaign.id)}
              className="px-3 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200 text-sm flex items-center gap-1"
            >
              <Trash2 className="w-4 h-4" /> Eliminar Campaña
            </button>
          </div>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
            <p className="text-blue-600 text-xs font-semibold uppercase">Total Leads</p>
            <p className="text-2xl font-bold text-blue-900">{selectedCampaign.total_leads || 0}</p>
          </div>
          <div className="bg-green-50 p-4 rounded-xl border border-green-100">
            <p className="text-green-600 text-xs font-semibold uppercase">Llamadas</p>
            <p className="text-2xl font-bold text-green-900">{selectedCampaign.called_leads || 0}</p>
          </div>
          <div className="bg-yellow-50 p-4 rounded-xl border border-yellow-100">
            <p className="text-yellow-600 text-xs font-semibold uppercase">Pendientes</p>
            <p className="text-2xl font-bold text-yellow-900">{selectedCampaign.pending_leads || 0}</p>
          </div>
          <div className="bg-red-50 p-4 rounded-xl border border-red-100">
            <p className="text-red-600 text-xs font-semibold uppercase">Fallidas</p>
            <p className="text-2xl font-bold text-red-900">{selectedCampaign.failed_leads || 0}</p>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
            <h3 className="font-semibold text-gray-900">Registro de Llamadas y Resultados</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-100">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Teléfono</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Estado e Intentos</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase w-1/3">Notas y Transcripción</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Última Actualización</th>
                  <th className="px-6 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {campaignLeads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{lead.phone_number}</td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-1 items-start">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium 
                                        ${lead.status === 'completed' ? 'bg-green-100 text-green-800' :
                            lead.status === 'called' ? 'bg-blue-100 text-blue-800' :
                              lead.status === 'failed' ? 'bg-red-100 text-red-800' :
                                lead.status === 'unreached' ? 'bg-orange-100 text-orange-800' :
                                  lead.status === 'incomplete' ? 'bg-purple-100 text-purple-800' :
                                    lead.status === 'rejected_opt_out' ? 'bg-red-200 text-red-900' : 'bg-gray-100 text-gray-800'}`}>
                          {lead.status === 'unreached' ? 'No Contestó' :
                            lead.status === 'rejected_opt_out' ? 'Rechazada' :
                              lead.status === 'completed' ? 'Completada' :
                                lead.status === 'incomplete' ? 'Incompleta' :
                                  lead.status === 'failed' ? 'Fallida' :
                                    lead.status === 'called' ? 'Llamada' :
                                      lead.status === 'pending' ? 'Pendiente' : lead.status}
                        </span>
                        {/* Mostrar intentos si > 0 */}
                        {(lead.retries_attempted || 0) > 0 && (
                          <span className="text-xs text-gray-500 flex items-center gap-1">
                            <History className="w-3 h-3" /> Intento: {lead.retries_attempted}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {(lead.puntuacion_comercial != null || lead.puntuacion_instalador != null || lead.puntuacion_rapidez != null) ? (
                        <div className="space-y-1">
                          <div className="flex gap-2">
                            <span className="font-bold text-gray-900">C:</span>{lead.puntuacion_comercial ?? '-'}
                            <span className="font-bold text-gray-900">I:</span>{lead.puntuacion_instalador ?? '-'}
                            <span className="font-bold text-gray-900">R:</span>{lead.puntuacion_rapidez ?? '-'}
                          </div>
                          {lead.comentarios && (
                            <p className="text-xs italic text-gray-500 border-l-2 border-gray-200 pl-2">"{lead.comentarios}"</p>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400 italic">
                          {lead.status === 'unreached' ? 'No contestó' :
                            lead.status === 'rejected_opt_out' ? 'Cliente rechazó la encuesta' :
                              lead.status === 'pending' ? 'Esperando...' : 'Sin datos todavía'}
                        </span>
                      )}

                      {/* Transcription Preview (Collapsible better, but inline for now) */}
                      {lead.transcription_preview && (
                        <details className="mt-1">
                          <summary className="text-xs text-blue-500 cursor-pointer hover:underline">Ver Transcripción</summary>
                          <p className="text-xs text-gray-500 mt-1 p-2 bg-gray-50 rounded whitespace-pre-wrap max-h-32 overflow-y-auto">
                            {lead.transcription_preview}
                          </p>
                        </details>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {lead.updated_at ? new Date(lead.updated_at).toLocaleString() : '-'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {['failed', 'unreached', 'incomplete'].includes(lead.status) && (() => {
                        const maxRetries = (selectedCampaign as any).retries_count || 3;
                        const remaining = Math.max(0, maxRetries - (lead.retries_attempted || 0));
                        return remaining > 0 ? (
                          <button
                            onClick={() => handleRetryLead(lead.id)}
                            className="text-xs bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 px-2 py-1 rounded shadow-sm inline-flex items-center gap-1 transition-all"
                            title="Reintentar esta llamada"
                          >
                            <Clock className="w-3 h-3 text-blue-500" />
                            Reintentar ({remaining} restantes)
                          </button>
                        ) : (
                          <span className="text-xs text-gray-400 italic">Sin reintentos</span>
                        );
                      })()}
                      {lead.status === 'completed' && (
                        <span className="text-xs text-green-600">✓ Completada</span>
                      )}
                      {lead.status === 'rejected_opt_out' && (
                        <span className="text-xs text-red-600">✗ Rechazada</span>
                      )}
                    </td>
                  </tr>
                ))}
                {campaignLeads.length === 0 && (
                  <tr><td colSpan={5} className="px-6 py-8 text-center text-gray-500">No hay leads en esta campaña</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
        {renderEditModal()}
      </div>
    );
  }

  // --- Main Campaign List View ---

  if (showCreate) {
    return (
      <div className="max-w-2xl mx-auto bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="p-6 border-b border-gray-100 flex justify-between items-center">
          <h2 className="text-xl font-bold">Create Campaign</h2>
          <button onClick={() => setShowCreate(false)} className="text-gray-400 hover:text-gray-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {error && (
            <div className="p-4 bg-red-50 text-red-600 rounded-lg text-sm flex items-center gap-2">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Campaign Name</label>
            <input
              type="text"
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent outline-none"
              placeholder="e.g. Q1 Customer Survey"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Agent</label>
            <select
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent outline-none"
              value={selectedAgent}
              onChange={(e) => setSelectedAgent(e.target.value)}
            >
              <option value="">Select an agent</option>
              {agents.map(a => (
                <option key={a.id} value={a.id}>{a.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Data Source Type</label>
            <select
              className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-black focus:border-transparent outline-none"
              value={dataSource}
              onChange={(e) => setDataSource(e.target.value as 'csv' | 'api' | 'manual')}
            >
              <option value="csv">CSV File</option>
              <option value="manual">Manual Entry / Copy-Paste</option>
              <option value="api">API Integration (Developer)</option>
            </select>
          </div>

          {dataSource === 'manual' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Enter Phones (and optional Names)</label>
              <textarea
                className="w-full px-4 py-2 border border-gray-200 rounded-lg h-32 font-mono text-sm focus:ring-2 focus:ring-black focus:border-transparent outline-none"
                placeholder={"+34600112233, Juan Perez\n+34600445566, Maria"}
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">One entry per line. Format: <code>Phone, Name</code> (Name is optional)</p>
            </div>
          ) : dataSource === 'csv' ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">CSV File</label>
              <div className="border-2 border-dashed border-gray-200 rounded-lg p-8 text-center hover:border-black transition-colors cursor-pointer relative">
                <input
                  type="file"
                  accept=".csv"
                  className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                />
                <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                <p className="text-sm text-gray-600">
                  {csvFile ? csvFile.name : 'Click to upload or drag and drop'}
                </p>
                <p className="text-xs text-gray-400 mt-1">.csv files only</p>
              </div>
              <div className="mt-2 text-right">
                <a
                  href="#"
                  onClick={(e) => {
                    e.preventDefault();
                    const csvContent = "phone,name\n+34600123456,Cliente Ejemplo\n+34600999999,Otro Cliente";
                    const blob = new Blob([csvContent], { type: 'text/csv' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = "plantilla_clientes.csv";
                    a.click();
                    window.URL.revokeObjectURL(url);
                  }}
                  className="text-xs text-blue-600 hover:underline flex items-center justify-end gap-1"
                >
                  <Upload className="w-3 h-3" /> Download Template
                </a>
              </div>
            </div>
          ) : (
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-600 mb-2">
                Use our API to programmatically add leads to this campaign.
              </p>
              <code className="text-xs bg-gray-100 p-2 block rounded overflow-x-auto">
                curl -X POST {API_URL}/api/campaigns/{'{id}'}/leads \
                -H "Content-Type: application/json" \
                -d '{'{ "phone": "+34600000000" }'}'
              </code>
            </div>
          )}

          <div className="border-t border-gray-100 pt-6">
            <button className="flex items-center justify-between w-full text-left font-medium text-gray-700">
              <span>Advanced Settings / Scheduling</span>
              <Clock className="w-4 h-4" />
            </button>
            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Schedule Start Time (Optional)</label>
              <input
                type="datetime-local"
                className="w-full px-4 py-2 border border-gray-200 rounded-lg"
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
              />
              <p className="text-xs text-gray-500 mt-1">Leave empty to start immediately.</p>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">Retry Interval (minutes)</label>
              <input
                type="number"
                min="1"
                className="w-full px-4 py-2 border border-gray-200 rounded-lg"
                value={retryInterval}
                onChange={(e) => setRetryInterval(Number(e.target.value))}
                placeholder="Default: 60"
              />
              <p className="text-xs text-gray-500 mt-1">Time to wait before retrying a failed call.</p>
            </div>
          </div>
        </div>

        <div className="p-6 bg-gray-50 border-t border-gray-100 flex justify-end gap-3">
          <button
            onClick={() => setShowCreate(false)}
            className="px-4 py-2 text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="px-4 py-2 bg-black text-white font-medium rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            {loading ? 'Creating...' : 'Launch Campaign'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Campaigns</h1>
          <p className="text-gray-500">Manage your bulk outbound call campaigns</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Campaign
        </button>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Campaign Name</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Status</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Progress</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Scheduled</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Created</th>
              <th className="px-6 py-4 text-right text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {campaigns.map((campaign) => (
              <tr key={campaign.id} className="hover:bg-gray-50 transition-colors cursor-pointer" onClick={() => loadCampaignDetails(campaign)}>
                <td className="px-6 py-4 text-sm font-medium text-gray-900">{campaign.name}</td>
                <td className="px-6 py-4">
                  <StatusBadge status={campaign.status} />
                </td>
                <td className="px-6 py-4 w-48">
                  {/* Progress Bar */}
                  <div className="flex flex-col gap-1">
                    <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-green-500"
                        style={{ width: `${((campaign.called_leads || 0) / (campaign.total_leads || 1)) * 100}%` }}
                      />
                    </div>
                    <div className="text-xs text-gray-500">
                      {campaign.called_leads || 0} / {campaign.total_leads || 0} calls
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {campaign.scheduled_time ? new Date(campaign.scheduled_time).toLocaleString() : '-'}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {campaign.created_at ? new Date(campaign.created_at).toLocaleDateString() : '-'}
                </td>
                <td className="px-6 py-4 text-right text-sm font-medium">
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={(e) => { e.stopPropagation(); openEditModal(campaign); }}
                      className="text-blue-600 hover:text-blue-900"
                      title="Edit Campaign"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (window.confirm('Delete campaign?')) {
                          handleDelete(campaign.id);
                        }
                      }}
                      className="text-red-600 hover:text-red-900"
                      title="Delete Campaign"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {campaigns.length === 0 && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                  No campaigns found. Create your first campaign to get started.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {renderEditModal()}
    </div>
  );
}
