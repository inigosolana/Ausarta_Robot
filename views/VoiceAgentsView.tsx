import React, { useState, useEffect } from 'react';
import { Save, Phone, Loader2, Bot, Mic, Speaker, Brain } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || window.location.origin + '/api' || 'http://localhost:8001/api';

interface AgentConfig {
  id?: string;
  name: string;
  useCase: string;
  description: string;
  instructions: string;
  greeting: string;
}

interface AIConfig {
  llm_provider: string;
  llm_model: string;
  tts_provider: string;
  tts_model: string;
  tts_voice: string;
  stt_provider: string;
  stt_model: string;
  language: string;
}

interface PromptTemplate {
  id: number;
  name: string;
  description: string;
  content: string;
}

const VoiceAgentsView: React.FC<{ onStartCall: () => void }> = ({ onStartCall }) => {
  const [agent, setAgent] = useState<AgentConfig>({
    name: '',
    useCase: '',
    description: '',
    instructions: '',
    greeting: ''
  });

  const [templates, setTemplates] = useState<PromptTemplate[]>([]);

  const [aiConfig, setAiConfig] = useState<AIConfig>({
    llm_provider: 'groq',
    llm_model: 'llama-3.3-70b-versatile',
    tts_provider: 'cartesia',
    tts_model: 'sonic-multilingual',
    tts_voice: 'fb926b21-4d92-411a-85d0-9d06859e2171',
    stt_provider: 'deepgram',
    stt_model: 'nova-2',
    language: 'es'
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  // Call Dialog State
  const [showCallDialog, setShowCallDialog] = useState(false);
  const [phoneNumber, setPhoneNumber] = useState('+34');
  const [isCalling, setIsCalling] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const [agentRes, aiRes, templatesRes] = await Promise.all([
        fetch(`${API_URL}/agents`),
        fetch(`${API_URL}/ai/config`),
        fetch(`${API_URL}/prompts`)
      ]);

      if (agentRes.ok) {
        const agents = await agentRes.json();
        if (agents.length > 0) setAgent(agents[0]);
      }

      if (aiRes.ok) {
        const aiData = await aiRes.json();
        if (Object.keys(aiData).length > 0) setAiConfig(aiData);
      }

      if (templatesRes.ok) {
        setTemplates(await templatesRes.json());
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);

      // Save Agent Config
      const agentPromise = fetch(`${API_URL}/agents/1`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(agent)
      });

      // Save AI Config
      const aiPromise = fetch(`${API_URL}/ai/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(aiConfig)
      });

      const [agentRes, aiRes] = await Promise.all([agentPromise, aiPromise]);

      if (agentRes.ok && aiRes.ok) {
        alert('✅ Configuración guardada correctamente');
      } else {
        alert('❌ Error al guardar la configuración');
      }
    } catch (error) {
      console.error('Error saving:', error);
      alert('Error al guardar');
    } finally {
      setIsSaving(false);
    }
  };

  const handleMakeCall = async () => {
    if (!phoneNumber || phoneNumber.length < 5) {
      alert('Número inválido');
      return;
    }

    try {
      setIsCalling(true);
      const response = await fetch(`${API_URL}/calls/outbound`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agentId: '1',
          phoneNumber: phoneNumber,
          agentName: agent.name
        })
      });

      const data = await response.json();
      if (response.ok) {
        alert(`✅ Llamada iniciada! Sala: ${data.roomName}`);
        setShowCallDialog(false);
        // onStartCall(); // Deshabilitamos el overlay de "Live Call" porque es engañoso para llamadas telefónicas
      } else {
        alert(`❌ Error: ${data.detail}`);
      }
    } catch (error) {
      alert('Error de conexión con el backend');
    } finally {
      setIsCalling(false);
    }
  };

  if (isLoading) return <div className="p-8 text-center text-gray-500">Cargando configuración...</div>;

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-20">
      <header className="flex justify-between items-center bg-white p-6 rounded-xl border border-gray-100 shadow-sm">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{agent.name || 'Ausarta Agent'}</h1>
          <p className="text-gray-500 text-sm">Configuración del Agente y Modelos AI</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowCallDialog(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-500 text-white font-medium rounded-lg hover:bg-green-600 transition-colors"
          >
            <Phone size={18} />
            Probar Llamada
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-2 px-4 py-2 bg-black text-white font-medium rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {isSaving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
            Guardar Cambios
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Columna Izquierda: Detalles del Agente */}
        <div className="md:col-span-2 space-y-6">
          {/* General Info */}
          <section className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm space-y-4">
            <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
              <Bot size={20} className="text-blue-500" />
              Identidad del Agente
            </h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Nombre del Agente</label>
                <input
                  type="text"
                  value={agent.name}
                  onChange={(e) => setAgent({ ...agent, name: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500/20 outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Caso de Uso</label>
                <input
                  type="text"
                  value={agent.useCase}
                  onChange={(e) => setAgent({ ...agent, useCase: e.target.value })}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500/20 outline-none"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Saludo Inicial</label>
              <input
                type="text"
                value={agent.greeting}
                onChange={(e) => setAgent({ ...agent, greeting: e.target.value })}
                placeholder="Hola, soy..."
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500/20 outline-none"
              />
              <p className="text-xs text-gray-400 mt-1">Lo primero que dirá el agente al contestar.</p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Descripción</label>
              <textarea
                rows={2}
                value={agent.description}
                onChange={(e) => setAgent({ ...agent, description: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500/20 outline-none resize-none"
              />
            </div>
          </section>

          {/* Instructions */}
          <section className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                <Brain size={20} className="text-purple-500" />
                Instrucciones (Prompt)
              </h3>

              <div className="flex items-center gap-2">
                {/* Selector de Templates */}
                <select
                  className="text-xs border border-gray-200 rounded-lg px-2 py-1.5 bg-gray-50 max-w-[150px]"
                  onChange={(e) => {
                    const template = templates.find(t => t.id === Number(e.target.value));
                    if (template) {
                      if (confirm('¿Reemplazar las instrucciones actuales con esta plantilla?')) {
                        setAgent({ ...agent, instructions: template.content });
                      }
                    }
                  }}
                  value=""
                >
                  <option value="" disabled>📂 Cargar Plantilla...</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>

                <button
                  onClick={async () => {
                    const name = prompt('Nombre para la nueva plantilla:');
                    if (name) {
                      try {
                        const res = await fetch(`${API_URL}/prompts`, {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify({
                            name,
                            description: 'Creado desde el editor',
                            content: agent.instructions
                          })
                        });
                        if (res.ok) {
                          alert('Plantilla guardada!');
                          loadData(); // Recargar templates
                        }
                      } catch (e) {
                        alert('Error al guardar plantilla');
                      }
                    }
                  }}
                  className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-lg border border-gray-200 transition-colors"
                >
                  💾 Guardar como Plantilla
                </button>
              </div>
            </div>

            <div className="relative">
              <textarea
                rows={15}
                value={agent.instructions}
                onChange={(e) => setAgent({ ...agent, instructions: e.target.value })}
                className="w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-purple-500/20 outline-none font-mono text-sm bg-gray-50"
              />
              <p className="text-xs text-gray-500 mt-2">Define aquí la personalidad, misión y reglas del agente.</p>
            </div>
          </section>
        </div>

        {/* Columna Derecha: Configuración AI */}
        <div className="space-y-6">

          {/* LLM Config */}
          <section className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
              <Brain size={16} /> Modelo de Lenguaje (LLM)
            </h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Proveedor</label>
              <select
                value={aiConfig.llm_provider}
                onChange={(e) => {
                  const newProvider = e.target.value;
                  let defaultModel = 'llama-3.3-70b-versatile';
                  if (newProvider === 'google') defaultModel = 'models/gemini-1.5-flash';
                  if (newProvider === 'openai') defaultModel = 'gpt-4o';
                  if (newProvider === 'deepseek') defaultModel = 'deepseek-chat';
                  setAiConfig({ ...aiConfig, llm_provider: newProvider, llm_model: defaultModel });
                }}
                className="w-full px-3 py-2 border rounded-lg bg-gray-50"
              >
                <option value="openai">OpenAI (GPT-4o)</option>
                <option value="groq">Groq (Llama 3, Mixtral)</option>
                <option value="google">Google Gemini</option>
                <option value="deepseek">DeepSeek (V3, R1)</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Modelo</label>
              <select
                value={aiConfig.llm_model}
                onChange={(e) => setAiConfig({ ...aiConfig, llm_model: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg bg-white"
              >
                {aiConfig.llm_provider === 'openai' ? (
                  <>
                    <option value="gpt-4o">GPT-4o (High Intelligence)</option>
                    <option value="gpt-4o-mini">GPT-4o mini (Fast & Cheap)</option>
                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  </>
                ) : aiConfig.llm_provider === 'google' ? (
                  <>
                    <option value="models/gemini-2.0-flash">Gemini 2.0 Flash</option>
                    <option value="models/gemini-2.0-flash-lite">Gemini 2.0 Flash Lite</option>
                    <option value="models/gemini-1.5-flash">Gemini 1.5 Flash</option>
                  </>
                ) : aiConfig.llm_provider === 'deepseek' ? (
                  <>
                    <option value="deepseek-chat">DeepSeek-V3 (Chat)</option>
                    <option value="deepseek-reasoner">DeepSeek-R1 (Reasoning)</option>
                  </>
                ) : (
                  <>
                    <option value="llama-3.3-70b-versatile">Llama 3.3 70B</option>
                    <option value="mixtral-8x7b-32768">Mixtral 8x7B</option>
                  </>
                )}
              </select>
            </div>
          </section>

          {/* TTS Config */}
          <section className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
              <Speaker size={16} /> Voz (TTS)
            </h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Proveedor</label>
              <select
                value={aiConfig.tts_provider}
                onChange={(e) => setAiConfig({ ...aiConfig, tts_provider: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg bg-gray-50"
              >
                <option value="cartesia">Cartesia (Sonic)</option>
                <option value="openai">OpenAI TTS</option>
                <option value="elevenlabs">ElevenLabs</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Modelo</label>
              <input
                type="text"
                value={aiConfig.tts_model}
                onChange={(e) => setAiConfig({ ...aiConfig, tts_model: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Voice ID</label>
              <input
                type="text"
                value={aiConfig.tts_voice}
                onChange={(e) => setAiConfig({ ...aiConfig, tts_voice: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg font-mono text-xs"
              />
            </div>
          </section>

          {/* STT Config */}
          <section className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
              <Mic size={16} /> Transcripción (STT)
            </h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Proveedor</label>
              <select
                value={aiConfig.stt_provider}
                onChange={(e) => setAiConfig({ ...aiConfig, stt_provider: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg bg-gray-50"
              >
                <option value="deepgram">Deepgram</option>
                <option value="openai">OpenAI Whisper</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Modelo</label>
              <input
                type="text"
                value={aiConfig.stt_model}
                onChange={(e) => setAiConfig({ ...aiConfig, stt_model: e.target.value })}
                className="w-full px-3 py-2 border rounded-lg"
              />
            </div>
          </section>

        </div>
      </div>

      {/* Diálogo para llamar */}
      {showCallDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 shadow-2xl max-w-md w-full mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-2">Probar Agente</h3>
            <p className="text-sm text-gray-500 mb-4">
              Llamar a tu teléfono para probar a <strong>{agent.name}</strong>
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-800 mb-2">Tu número de teléfono</label>
                <input
                  type="tel"
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  placeholder="+34600123456"
                  className="w-full h-10 px-4 bg-white border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/10 focus:border-blue-500 transition-all font-mono"
                  disabled={isCalling}
                />
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setShowCallDialog(false)}
                  className="flex-1 py-2.5 bg-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-300 transition-colors"
                  disabled={isCalling}
                >
                  Cancelar
                </button>
                <button
                  onClick={handleMakeCall}
                  className="flex-1 py-2.5 bg-green-500 text-white text-sm font-medium rounded-lg hover:bg-green-600 transition-colors shadow-sm flex items-center justify-center gap-2"
                  disabled={isCalling}
                >
                  {isCalling ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
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
