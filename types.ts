
export type ViewState = 
  | 'overview' 
  | 'voice-agents' 
  | 'campaigns' 
  | 'automation' 
  | 'models' 
  | 'telephony' 
  | 'tools' 
  | 'files' 
  | 'developers'
  | 'usage'
  | 'reports'
  | 'looptalk';

export interface Campaign {
  id: string;
  name: string;
  workflow: string;
  status: 'active' | 'draft' | 'completed';
  createdAt: string;
}

export interface VoiceAgent {
  id: string;
  name: string;
  callType: 'Inbound' | 'Outbound';
  useCase: string;
  description: string;
}

export interface TelephonyConfig {
  provider: string;
  fromNumbers: string;
}

export interface ModelConfig {
  llmProvider: string;
  voiceProvider: string;
  transcriberProvider: string;
  embeddingProvider: string;
}
