
import React, { useState, useEffect, useRef } from 'react';
import { X, Mic, MicOff, PhoneOff, AudioWaveform } from 'lucide-react';
import { GoogleGenAI, LiveServerMessage, Modality, Blob } from '@google/genai';

interface LiveCallViewProps {
  onClose: () => void;
}

const LiveCallView: React.FC<LiveCallViewProps> = ({ onClose }) => {
  const [isConnecting, setIsConnecting] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [transcript, setTranscript] = useState<string[]>([]);
  const [volume, setVolume] = useState(0);

  const audioCtxRef = useRef<AudioContext | null>(null);
  const outputCtxRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const sourcesRef = useRef(new Set<AudioBufferSourceNode>());
  const sessionRef = useRef<any>(null);

  useEffect(() => {
    startSession();
    return () => {
      stopSession();
    };
  }, []);

  const decode = (base64: string) => {
    const binaryString = atob(base64);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
  };

  const decodeAudioData = async (
    data: Uint8Array,
    ctx: AudioContext,
    sampleRate: number,
    numChannels: number,
  ): Promise<AudioBuffer> => {
    const dataInt16 = new Int16Array(data.buffer);
    const frameCount = dataInt16.length / numChannels;
    const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

    for (let channel = 0; channel < numChannels; channel++) {
      const channelData = buffer.getChannelData(channel);
      for (let i = 0; i < frameCount; i++) {
        channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
      }
    }
    return buffer;
  };

  const encode = (bytes: Uint8Array) => {
    let binary = '';
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  };

  const createBlob = (data: Float32Array): Blob => {
    const l = data.length;
    const int16 = new Int16Array(l);
    for (let i = 0; i < l; i++) {
      int16[i] = data[i] * 32768;
    }
    return {
      data: encode(new Uint8Array(int16.buffer)),
      mimeType: 'audio/pcm;rate=16000',
    };
  };

  const startSession = async () => {
    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY || '' });
      
      const inputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      const outputAudioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 });
      audioCtxRef.current = inputAudioContext;
      outputCtxRef.current = outputAudioContext;

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        callbacks: {
          onopen: () => {
            setIsConnecting(false);
            setIsConnected(true);
            
            const source = inputAudioContext.createMediaStreamSource(stream);
            const scriptProcessor = inputAudioContext.createScriptProcessor(4096, 1, 1);
            
            scriptProcessor.onaudioprocess = (e) => {
              if (isMuted) return;
              const inputData = e.inputBuffer.getChannelData(0);
              
              // Simple volume detection for visualizer
              let sum = 0;
              for(let i=0; i<inputData.length; i++) sum += inputData[i] * inputData[i];
              setVolume(Math.sqrt(sum / inputData.length) * 100);

              const pcmBlob = createBlob(inputData);
              sessionPromise.then(session => {
                session.sendRealtimeInput({ media: pcmBlob });
              });
            };
            
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputAudioContext.destination);
          },
          onmessage: async (message: LiveServerMessage) => {
            if (message.serverContent?.outputTranscription) {
              const text = message.serverContent.outputTranscription.text;
              setTranscript(prev => [...prev.slice(-4), `AI: ${text}`]);
            } else if (message.serverContent?.inputTranscription) {
              const text = message.serverContent.inputTranscription.text;
              setTranscript(prev => [...prev.slice(-4), `You: ${text}`]);
            }

            const base64Audio = message.serverContent?.modelTurn?.parts[0]?.inlineData?.data;
            if (base64Audio) {
              nextStartTimeRef.current = Math.max(nextStartTimeRef.current, outputAudioContext.currentTime);
              const audioBuffer = await decodeAudioData(decode(base64Audio), outputAudioContext, 24000, 1);
              const source = outputAudioContext.createBufferSource();
              source.buffer = audioBuffer;
              source.connect(outputAudioContext.destination);
              source.start(nextStartTimeRef.current);
              nextStartTimeRef.current += audioBuffer.duration;
              sourcesRef.current.add(source);
              source.onended = () => sourcesRef.current.delete(source);
            }

            if (message.serverContent?.interrupted) {
              sourcesRef.current.forEach(s => s.stop());
              sourcesRef.current.clear();
              nextStartTimeRef.current = 0;
            }
          },
          onerror: (e) => {
            console.error('Gemini Live error:', e);
            setIsConnecting(false);
          },
          onclose: () => {
            setIsConnected(false);
          }
        },
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } },
          },
          systemInstruction: 'You are an expert AI voice agent for Ausarta Robot. Your goal is to help the user configure their dashboard and explain how voice calls work. Be concise, professional, and friendly. Answer in the user\'s language.',
          inputAudioTranscription: {},
          outputAudioTranscription: {}
        }
      });

      sessionRef.current = await sessionPromise;
    } catch (err) {
      console.error('Failed to start session:', err);
      setIsConnecting(false);
    }
  };

  const stopSession = () => {
    if (sessionRef.current) {
      sessionRef.current.close();
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close();
    }
    if (outputCtxRef.current) {
      outputCtxRef.current.close();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-white w-full max-w-md rounded-2xl shadow-2xl overflow-hidden flex flex-col min-h-[500px]">
        {/* Header */}
        <div className="p-4 flex items-center justify-between border-b border-gray-50 bg-gray-50/30">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
            <span className="text-sm font-bold text-gray-800">Agent Live Call</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-gray-200 rounded-full transition-colors text-gray-500">
            <X size={18} />
          </button>
        </div>

        {/* Call Body */}
        <div className="flex-1 p-8 flex flex-col items-center justify-center space-y-8">
          <div className="relative">
            {/* Visualizer Circle */}
            <div className="w-32 h-32 rounded-full bg-gray-50 flex items-center justify-center relative overflow-hidden">
               {/* Pulsing rings */}
               {isConnected && (
                 <>
                   <div className="absolute inset-0 bg-blue-400/20 rounded-full animate-ping" style={{ animationDuration: '2s' }} />
                   <div className="absolute inset-0 bg-blue-500/10 rounded-full animate-ping" style={{ animationDuration: '3s' }} />
                 </>
               )}
               <div className="w-16 h-16 rounded-full bg-white shadow-lg flex items-center justify-center z-10">
                 <Mic size={32} className={`${isConnected ? 'text-blue-600' : 'text-gray-300'}`} />
               </div>
            </div>
            {/* Dynamic Volume bars */}
            {isConnected && (
              <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 flex gap-1 h-8 items-end">
                {[...Array(5)].map((_, i) => (
                  <div 
                    key={i} 
                    className="w-1.5 bg-blue-500 rounded-full transition-all duration-75"
                    style={{ height: `${10 + Math.random() * volume}%` }}
                  />
                ))}
              </div>
            )}
          </div>

          <div className="text-center">
            <h2 className="text-xl font-bold text-gray-900">
              {isConnecting ? 'Establishing connection...' : isConnected ? 'AI Agent connected' : 'Call ended'}
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              {isConnected ? 'Speaking with AI Voice Agent...' : 'Connecting to Gemini Live API...'}
            </p>
          </div>

          {/* Transcript Area */}
          <div className="w-full bg-gray-50/50 rounded-xl p-4 h-32 overflow-y-auto border border-gray-100">
            {transcript.length === 0 ? (
              <p className="text-xs text-gray-400 italic text-center mt-8">Transcripts will appear here...</p>
            ) : (
              <div className="space-y-2">
                {transcript.map((line, idx) => (
                  <p key={idx} className="text-[11px] text-gray-600 leading-tight">
                    {line}
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Controls */}
        <div className="p-8 border-t border-gray-50 bg-gray-50/20 flex items-center justify-center gap-6">
          <button 
            onClick={() => setIsMuted(!isMuted)}
            className={`p-4 rounded-full shadow-md transition-all ${isMuted ? 'bg-red-50 text-red-500' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
          >
            {isMuted ? <MicOff size={24} /> : <Mic size={24} />}
          </button>
          
          <button 
            onClick={onClose}
            className="p-5 bg-red-500 text-white rounded-full shadow-lg hover:bg-red-600 transition-all hover:scale-110 active:scale-95"
          >
            <PhoneOff size={28} />
          </button>

          <button className="p-4 rounded-full bg-white shadow-md text-gray-600 hover:bg-gray-50 transition-all">
            <AudioWaveform size={24} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default LiveCallView;
