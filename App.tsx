
import React, { useState } from 'react';
import {
  LayoutDashboard,
  Mic2,
  Megaphone,
  Zap,
  Cpu,
  PhoneCall,
  Wrench,
  MessageSquare,
  BarChart3,
  ClipboardList,
  PanelLeftClose,
  PanelLeftOpen,
  Github
} from 'lucide-react';
import { ViewState } from './types';
import SidebarItem from './components/SidebarItem';
import TelephonyView from './views/TelephonyView';
import ModelsView from './views/ModelsView';
import { CampaignsView } from './views/CampaignsView';
import VoiceAgentsView from './views/VoiceAgentsView';
import LiveCallView from './views/LiveCallView';
import DashboardView from './views/DashboardView';
import ResultsView from './views/ResultsView';
import UsageView from './views/UsageView';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewState | 'results'>('overview');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isCalling, setIsCalling] = useState(false);

  const renderContent = () => {
    switch (currentView) {
      case 'telephony':
        return <TelephonyView />;
      case 'campaigns':
        return <CampaignsView />;
      case 'voice-agents':
        return <VoiceAgentsView onStartCall={() => setIsCalling(true)} />;
      case 'overview':
        return <DashboardView />;
      case 'results':
        return <ResultsView />;
      case 'usage':
        return <UsageView />;
      case 'models':
        return <ModelsView />;
      case 'automation':
      case 'tools':
      default:
        return (
          <div className="flex items-center justify-center h-full text-gray-400">
            <div className="text-center">
              <BarChart3 size={48} className="mx-auto mb-4 opacity-20" />
              <p>Módulo "{currentView}" en desarrollo o no implementado aún.</p>
            </div>
          </div>
        );
    }
  };

  const [alerts, setAlerts] = useState<any[]>([]);
  const API_URL = import.meta.env.VITE_API_URL || window.location.origin;

  React.useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await fetch(`${API_URL}/api/alerts`);
        if (res.ok) {
          const data = await res.json();
          setAlerts(data);
        }
      } catch (e) {
        // Silent error
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 10000); // Check every 10s
    return () => clearInterval(interval);
  }, []);

  const resolveAlert = async (id: number) => {
    try {
      await fetch(`${API_URL}/api/alerts/${id}/resolve`, { method: 'POST' });
      setAlerts(prev => prev.filter(a => a.id !== id));
    } catch (e) { }
  };

  return (
    <div className="flex h-screen w-full bg-[#fcfcfc] overflow-hidden">
      {/* Sidebar */}
      <aside className={`${isSidebarOpen ? 'w-64' : 'w-20'} border-r border-gray-100 bg-white flex flex-col transition-all duration-300 ease-in-out`}>
        <div className="p-4 flex items-center justify-between border-b border-gray-50">
          <div className={`flex items-center gap-3 font-bold text-gray-800 overflow-hidden ${!isSidebarOpen && 'hidden'}`}>
            <img src="/ausarta.png" alt="Ausarta Logo" className="h-8 w-auto object-contain" />
            <div className="flex flex-col">
              <span className="text-lg leading-none tracking-tight">Ausarta</span>
              <span className="text-[10px] text-gray-400 font-normal">Voice AI v1.14</span>
            </div>
          </div>
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-1 hover:bg-gray-50 rounded text-gray-400">
            {isSidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
          </button>
        </div>

        <div className="p-3">
          <button className="flex items-center gap-2 w-full px-3 py-2 text-sm text-yellow-600 bg-yellow-50/50 hover:bg-yellow-50 rounded-lg font-medium transition-colors">
            <Github size={16} className="text-yellow-600" />
            {isSidebarOpen && "Star us on GitHub"}
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-3 py-2 space-y-1">
          <SidebarItem
            icon={<LayoutDashboard size={18} />}
            label="Overview"
            isActive={currentView === 'overview'}
            onClick={() => setCurrentView('overview')}
            collapsed={!isSidebarOpen}
          />

          <div className={`mt-6 mb-2 px-3 text-[10px] uppercase tracking-wider font-bold text-gray-400 ${!isSidebarOpen && 'hidden'}`}>
            Build
          </div>
          <SidebarItem
            icon={<Mic2 size={18} />}
            label="Voice Agents"
            isActive={currentView === 'voice-agents'}
            onClick={() => setCurrentView('voice-agents')}
            collapsed={!isSidebarOpen}
          />
          <SidebarItem
            icon={<Megaphone size={18} />}
            label="Campaigns"
            isActive={currentView === 'campaigns'}
            onClick={() => setCurrentView('campaigns')}
            collapsed={!isSidebarOpen}
          />
          <SidebarItem
            icon={<Zap size={18} />}
            label="Automation"
            isActive={currentView === 'automation'}
            onClick={() => setCurrentView('automation')}
            collapsed={!isSidebarOpen}
          />
          <SidebarItem
            icon={<Cpu size={18} />}
            label="AI Models"
            isActive={currentView === 'models'}
            onClick={() => setCurrentView('models')}
            collapsed={!isSidebarOpen}
          />
          <SidebarItem
            icon={<PhoneCall size={18} />}
            label="Telephony"
            isActive={currentView === 'telephony'}
            onClick={() => setCurrentView('telephony')}
            collapsed={!isSidebarOpen}
          />
          <SidebarItem
            icon={<Wrench size={18} />}
            label="Tools"
            isActive={currentView === 'tools'}
            onClick={() => setCurrentView('tools')}
            collapsed={!isSidebarOpen}
          />

          <div className={`mt-6 mb-2 px-3 text-[10px] uppercase tracking-wider font-bold text-gray-400 ${!isSidebarOpen && 'hidden'}`}>
            Observe
          </div>
          <SidebarItem
            icon={<ClipboardList size={18} />}
            label="Results"
            isActive={currentView === 'results'}
            onClick={() => setCurrentView('results')}
            collapsed={!isSidebarOpen}
          />
          <SidebarItem
            icon={<BarChart3 size={18} />}
            label="Usage"
            isActive={currentView === 'usage'}
            onClick={() => setCurrentView('usage')}
            collapsed={!isSidebarOpen}
          />
        </nav>

        <div className="p-4 border-t border-gray-50">
          <button className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-900 w-full px-2 py-1">
            <MessageSquare size={16} />
            {isSidebarOpen && "Get Help"}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-8 relative">
        <div className="max-w-6xl mx-auto">
          {alerts.length > 0 && (
            <div className="mb-6 space-y-2">
              {alerts.map((alert: any) => (
                <div key={alert.id} className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg flex items-center justify-between shadow-sm animate-pulse">
                  <div className="flex items-center gap-3">
                    <div className="bg-red-100 p-2 rounded-full">
                      <Zap className="w-5 h-5 text-red-600" />
                    </div>
                    <div>
                      <h3 className="font-bold text-sm uppercase">{alert.type === 'api_limit' ? '⚠️ API Limit Reached' : 'System Alert'}</h3>
                      <p className="text-sm">{alert.message}</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {alert.type === 'api_limit' && (
                      <button
                        onClick={() => setCurrentView('voice-agents')}
                        className="px-3 py-1 bg-white border border-red-200 rounded text-xs font-semibold hover:bg-red-50"
                      >
                        Manage API Keys
                      </button>
                    )}
                    <button
                      onClick={() => resolveAlert(alert.id)}
                      className="px-3 py-1 bg-red-100 rounded text-xs hover:bg-red-200"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          {renderContent()}
        </div>
      </main>

      {/* Live Call Overlay */}
      {isCalling && (
        <LiveCallView onClose={() => setIsCalling(false)} />
      )}
    </div>
  );
};

export default App;
