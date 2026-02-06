
import React, { useState } from 'react';
import {
  LayoutDashboard,
  Mic2,
  Megaphone,
  Zap,
  Cpu,
  PhoneCall,
  Wrench,
  FileText,
  Code2,
  BarChart3,
  ClipboardList,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Github,
  ChevronRight,
  Plus
} from 'lucide-react';
import { ViewState } from './types';
import SidebarItem from './components/SidebarItem';
import TelephonyView from './views/TelephonyView';
import ModelsView from './views/ModelsView';
import CampaignsView from './views/CampaignsView';
import VoiceAgentsView from './views/VoiceAgentsView';
import LiveCallView from './views/LiveCallView';
import DashboardView from './views/DashboardView';
import ResultsView from './views/ResultsView';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<ViewState | 'results'>('overview');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isCalling, setIsCalling] = useState(false);

  const renderContent = () => {
    switch (currentView) {
      case 'telephony':
        return <TelephonyView />;
      case 'models':
        return <ModelsView />;
      case 'campaigns':
        return <CampaignsView />;
      case 'voice-agents':
        return <VoiceAgentsView onStartCall={() => setIsCalling(true)} />;
      case 'overview':
        return <DashboardView />;
      case 'results':
        return <ResultsView />;
      default:
        return (
          <div className="flex items-center justify-center h-full text-gray-400">
            <p>Feature under development: {currentView}</p>
          </div>
        );
    }
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
              <span className="text-[10px] text-gray-400 font-normal">Voice AI v1.12</span>
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
            label="Models"
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
