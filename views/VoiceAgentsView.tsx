
import React, { useState, useEffect } from 'react';
import { Plus, X, ChevronDown, Phone, Play } from 'lucide-react';

// API URL - En producción Docker usa nginx proxy, en desarrollo usa localhost
const API_URL = import.meta.env.VITE_API_URL || window.location.origin + '/api' || 'http://localhost:8001/api';

interface VoiceAgentsViewProps {
  onStartCall: () => void;
}

interface Agent {
  id: string;
  name: string;
  callType: string;
  useCase: string;
  description: string;
}

const VoiceAgentsView: React.FC<VoiceAgentsViewProps> = ({ onStartCall }) => {
  const [isCreating, setIsCreating] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [newAgent, setNewAgent] = useState({
    name: '',
    callType: 'Outbound',
    useCase: '',
    description: ''
  });

  // Estado para el diálogo de llamada
  const [showCallDialog, setShowCallDialog] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [phoneNumber, setPhoneNumber] = useState('+34');
  const [isLoading, setIsLoading] = useState(false);

  // Cargar agentes al montar
  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const response = await fetch(`${API_URL}/agents`);
      const data = await response.json();
      setAgents(data);
    } catch (error) {
      console.error('Error loading agents:', error);
    }
  };

  const handleCreateAgent = async () => {
    if (!newAgent.name || !newAgent.useCase || !newAgent.description) {
      alert('Por favor, completa todos los campos');
      return;
    }

    try {
      const response = await fetch(`${API_URL}/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAgent)
      });

      if (response.ok) {
        await loadAgents();
        setIsCreating(false);
        setNewAgent({ name: '', callType: 'Outbound', useCase: '', description: '' });
      }
    } catch (error) {
      console.error('Error creating agent:', error);
      alert('Error al crear el agente');
    }
  };

  const handleStartCall = (agent: Agent) => {
    setSelectedAgent(agent);
    setShowCallDialog(true);
  };

  const handleMakeCall = async () => {
    if (!phoneNumber || phoneNumber.length < 5) {
      alert('Ingresa un número de teléfono válido');
      return;
    }

    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/calls/outbound`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId: selectedAgent?.id,
          phoneNumber: phoneNumber
        })
      });

      const data = await response.json();

      if (response.ok) {
        alert(`✅ Llamada iniciada correctamente!\nSala: ${data.roomName}\nID: ${data.callId}`);
        setShowCallDialog(false);
        setPhoneNumber('+34');
        onStartCall();
      } else {
        alert(`❌ Error: ${data.detail}`);
      }
    } catch (error) {
      console.error('Error making call:', error);
      alert('Error al iniciar la llamada. Asegúrate de que el backend esté corriendo.');
    } finally {
      setIsLoading(false);
    }
  };

  if (isCreating) {
    return (
      <div className="space-y-6">
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Create Voice Agent</h1>
            <p className="text-gray-500 text-sm mt-1">Tell us about your use case and we'll create a customized voice agent for you</p>
          </div>
          <button onClick={() => setIsCreating(false)} className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-400">
            <X size={20} />
          </button>
        </header>

        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 space-y-6">
          <h3 className="text-base font-bold text-gray-900">Agent Details</h3>
          <p className="text-xs text-gray-400 -mt-5">Configure your voice agent settings</p>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Call Type</label>
              <div className="relative">
                <select
                  value={newAgent.callType}
                  onChange={(e) => setNewAgent({ ...newAgent, callType: e.target.value })}
                  className="w-full h-10 px-4 pr-10 appearance-none bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all cursor-pointer"
                >
                  <option value="Inbound">Inbound (Users call AI)</option>
                  <option value="Outbound">Outbound (AI calls users)</option>
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" size={16} />
              </div>
              <p className="text-[11px] text-gray-400 mt-1">Choose whether users will call your AI or your AI will call users</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Agent Name</label>
              <input
                type="text"
                placeholder="e.g., Encuesta Calidad Ausarta"
                value={newAgent.name}
                onChange={(e) => setNewAgent({ ...newAgent, name: e.target.value })}
                className="w-full h-10 px-4 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
              <p className="text-[11px] text-gray-400 mt-1">Give your agent a descriptive name</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Use Case</label>
              <input
                type="text"
                placeholder="e.g., Lead Qualification, HR Screening, Customer Support"
                value={newAgent.useCase}
                onChange={(e) => setNewAgent({ ...newAgent, useCase: e.target.value })}
                className="w-full h-10 px-4 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
              />
              <p className="text-[11px] text-gray-400 mt-1">Describe the primary purpose of your voice agent</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-1">Activity Description</label>
              <textarea
                rows={4}
                placeholder="Describe briefly what your voice agent will do (e.g., Qualify leads for real estate, Screen candidates for roles, Handle customer support). This will be a prompt to an LLM."
                value={newAgent.description}
                onChange={(e) => setNewAgent({ ...newAgent, description: e.target.value })}
                className="w-full px-4 py-3 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all resize-none"
              />
              <p className="text-[11px] text-gray-400 mt-1">This description will be used to generate the AI prompt for your voice agent</p>
            </div>
          </div>

          <div className="flex gap-3 pt-4">
            <button onClick={handleCreateAgent} className="flex-1 py-2.5 bg-[#121212] text-white text-sm font-medium rounded-lg hover:bg-black transition-colors shadow-sm">
              Create Agent
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Voice Agents</h1>
          <p className="text-gray-500 text-sm mt-1">Design and manage your AI-powered voice representatives</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2 bg-[#121212] text-white text-sm font-medium rounded-lg hover:bg-black transition-colors shadow-sm"
        >
          <Plus size={18} />
          New Agent
        </button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {agents.map((agent) => (
          <div key={agent.id} className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow group">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="font-bold text-gray-900">{agent.name}</h3>
                <span className="text-[10px] uppercase tracking-wider font-bold text-blue-500 bg-blue-50 px-2 py-0.5 rounded-full">{agent.callType}</span>
              </div>
              <button
                onClick={() => handleStartCall(agent)}
                className="p-2 bg-green-500 text-white rounded-full hover:bg-green-600 transition-colors shadow-sm group-hover:scale-110"
              >
                <Phone size={16} fill="white" />
              </button>
            </div>
            <p className="text-sm text-gray-600 line-clamp-2 mb-4">{agent.description}</p>
            <div className="flex items-center gap-4 text-[11px] text-gray-400 font-medium">
              <span>Use Case: {agent.useCase}</span>
              <span>•</span>
              <span>Modified 2h ago</span>
            </div>
          </div>
        ))}

        <button
          onClick={() => setIsCreating(true)}
          className="border-2 border-dashed border-gray-100 rounded-xl p-6 flex flex-col items-center justify-center text-gray-400 hover:border-gray-200 hover:text-gray-500 transition-all min-h-[160px]"
        >
          <Plus size={24} className="mb-2" />
          <span className="text-sm font-medium">Create New Agent</span>
        </button>
      </div>

      {/* Diálogo para ingresar número de teléfono */}
      {showCallDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 shadow-2xl max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Iniciar Llamada Outbound</h3>
            <p className="text-sm text-gray-500 mb-4">
              Agente: <strong>{selectedAgent?.name}</strong>
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-800 mb-2">Número de teléfono</label>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+34621151394"
                  className="w-full h-10 px-4 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all"
                  disabled={isLoading}
                />
                <p className="text-[11px] text-gray-400 mt-1">Incluye el código de país (ej. +34 para España)</p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => {
                    setShowCallDialog(false);
                    setPhoneNumber('+34');
                  }}
                  className="flex-1 py-2.5 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300 transition-colors"
                  disabled={isLoading}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleMakeCall}
                  className="flex-1 py-2.5 bg-green-500 text-white text-sm font-medium rounded-lg hover:bg-green-600 transition-colors shadow-sm flex items-center justify-center gap-2"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                      Llamando...
                    </>
                  ) : (
                    <>
                      <Phone size={16} />
                      Llamar Ahora
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceAgentsView;
