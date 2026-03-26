

// // import React, { useState, useRef, useEffect, useCallback } from 'react';
// // import { voiceChatAPI } from '../../services/api';

// // /* ═══════════════════════════════════════════════════════════════════════════
// //    DOIT-BOT · Azure Whisper + GPT-4o-mini + Azure TTS
// //    Glass Sphere LED Robot → Click to activate → Speak → Agent replies in voice
   
// //    ARCHITECTURE:
// //    - Frontend: MediaRecorder → Audio blob
// //    - Backend: Azure Whisper (STT) → GPT-4o-mini → Azure TTS
// //    - Frontend: Audio stream playback
// //    ═══════════════════════════════════════════════════════════════════════════ */

// // /* ─── LED dot-matrix definitions ──────────────────────────────────────────── */
// // const GAP = 10, OX = 22, OY = 52, DOT = 4.2;

// // const EXPRESSIONS = {
// //   idle: {
// //     leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
// //     rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
// //     mouth:    [[4,3],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,3]],
// //   },
// //   listening: {
// //     leftEye:  [[2,0],[3,0],[4,0],[5,0],[6,0]],
// //     rightEye: [[10,0],[11,0],[12,0],[13,0],[14,0]],
// //     mouth:    [[6,3],[7,3],[8,3],[9,3],[10,3]],
// //   },
// //   thinking: {
// //     leftEye:  [[2,0],[3,1],[4,0],[5,1],[6,0]],
// //     rightEye: [[10,0],[11,1],[12,0],[13,1],[14,0]],
// //     mouth:    [[5,3],[6,3],[7,3],[9,3],[10,3],[11,3]],
// //   },
// //   speaking: {
// //     leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
// //     rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
// //     mouth:    [[4,3],[5,3],[6,3],[7,3],[8,3],[9,3],[10,3],[11,3],
// //                [4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4]],
// //   },
// //   happy: {
// //     leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
// //     rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
// //     mouth:    [[3,3],[4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4],[12,3]],
// //   },
// //   error: {
// //     leftEye:  [[2,0],[3,0],[4,1],[5,0],[6,0]],
// //     rightEye: [[10,0],[11,0],[12,1],[13,0],[14,0]],
// //     mouth:    [[4,4],[5,3],[6,3],[7,3],[8,3],[9,3],[10,3],[11,4]],
// //   },
// // };

// // /* ─── SVG Components ──────────────────────────────────────────────────────── */
// // function LedFace({ expression = 'idle', glowColor = '#38bdf8' }) {
// //   const expr = EXPRESSIONS[expression] || EXPRESSIONS.idle;
// //   const dots = [...expr.leftEye, ...expr.rightEye, ...expr.mouth];
// //   return (
// //     <>
// //       {dots.map(([gx, gy], i) => (
// //         <circle
// //           key={i}
// //           cx={OX + gx * GAP}
// //           cy={OY + gy * GAP}
// //           r={DOT}
// //           fill={glowColor}
// //           style={{
// //             filter: `drop-shadow(0 0 5px ${glowColor}) drop-shadow(0 0 10px ${glowColor}88)`,
// //             transition: 'all 0.12s ease',
// //           }}
// //         />
// //       ))}
// //     </>
// //   );
// // }

// // function RobotSphere({ expression, size = 80, glowColor = '#38bdf8', pulsing = false }) {
// //   const uid = `rs_${size}`;
// //   return (
// //     <svg
// //       width={size} height={size}
// //       viewBox="0 0 180 200"
// //       xmlns="http://www.w3.org/2000/svg"
// //       style={{
// //         display: 'block',
// //         filter: pulsing
// //           ? `drop-shadow(0 0 18px ${glowColor}) drop-shadow(0 8px 24px ${glowColor}66)`
// //           : `drop-shadow(0 8px 24px ${glowColor}44) drop-shadow(0 2px 8px rgba(0,0,0,0.5))`,
// //         transition: 'filter 0.35s ease',
// //       }}
// //     >
// //       <defs>
// //         <linearGradient id={`chrome_${uid}`} x1="0" y1="0" x2="1" y2="1">
// //           <stop offset="0%" stopColor="#9ca3af" />
// //           <stop offset="30%" stopColor="#e5e7eb" />
// //           <stop offset="60%" stopColor="#6b7280" />
// //           <stop offset="100%" stopColor="#374151" />
// //         </linearGradient>
// //         <radialGradient id={`sphere_${uid}`} cx="38%" cy="30%" r="65%">
// //           <stop offset="0%" stopColor="#1e293b" stopOpacity="0.7" />
// //           <stop offset="60%" stopColor="#0f172a" stopOpacity="0.92" />
// //           <stop offset="100%" stopColor="#020617" />
// //         </radialGradient>
// //         <radialGradient id={`sheen_${uid}`} cx="30%" cy="22%" r="50%">
// //           <stop offset="0%" stopColor="white" stopOpacity="0.3" />
// //           <stop offset="100%" stopColor="white" stopOpacity="0" />
// //         </radialGradient>
// //         <radialGradient id={`glow_${uid}`} cx="50%" cy="90%" r="50%">
// //           <stop offset="0%" stopColor={glowColor} stopOpacity="0.2" />
// //           <stop offset="100%" stopColor={glowColor} stopOpacity="0" />
// //         </radialGradient>
// //         <radialGradient id={`cap_${uid}`} cx="35%" cy="30%" r="65%">
// //           <stop offset="0%" stopColor={glowColor} />
// //           <stop offset="100%" stopColor={glowColor} stopOpacity="0.4" />
// //         </radialGradient>
// //         <linearGradient id={`ear_${uid}`} x1="0" y1="0" x2="1" y2="1">
// //           <stop offset="0%" stopColor="#374151" />
// //           <stop offset="100%" stopColor="#111827" />
// //         </linearGradient>
// //       </defs>
// //       <line x1="108" y1="8" x2="120" y2="30" stroke="#9ca3af" strokeWidth="2.5" strokeLinecap="round"/>
// //       <circle cx="120" cy="28" r="5" fill={`url(#cap_${uid})`}
// //         style={{ filter: `drop-shadow(0 0 6px ${glowColor})` }} />
// //       <circle cx="90" cy="98" r="76" fill={`url(#chrome_${uid})`} />
// //       <circle cx="90" cy="98" r="68" fill={`url(#sphere_${uid})`} />
// //       <LedFace expression={expression} glowColor={glowColor} />
// //       <ellipse cx="72" cy="72" rx="46" ry="36" fill={`url(#sheen_${uid})`} />
// //       <circle cx="90" cy="98" r="68" fill={`url(#glow_${uid})`} />
// //       <ellipse cx="16" cy="98" rx="10" ry="14" fill={`url(#ear_${uid})`} stroke="#4b5563" strokeWidth="1"/>
// //       <ellipse cx="16" cy="98" rx="5" ry="8" fill={glowColor} opacity="0.25" />
// //       <ellipse cx="164" cy="98" rx="10" ry="14" fill={`url(#ear_${uid})`} stroke="#4b5563" strokeWidth="1"/>
// //       <ellipse cx="164" cy="98" rx="5" ry="8" fill={glowColor} opacity="0.25" />
// //       <polygon points="74,170 88,163 88,177" fill="#1e293b" stroke="#374151" strokeWidth="1"/>
// //       <polygon points="106,170 92,163 92,177" fill="#1e293b" stroke="#374151" strokeWidth="1"/>
// //       <ellipse cx="90" cy="170" rx="6" ry="5" fill="#374151" stroke="#4b5563" strokeWidth="1"/>
// //     </svg>
// //   );
// // }

// // function VoiceRings({ active, color }) {
// //   if (!active) return null;
// //   return (
// //     <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
// //       {[0, 1, 2].map(i => (
// //         <div key={i} style={{
// //           position: 'absolute',
// //           width: `${90 + i * 38}px`, height: `${90 + i * 38}px`,
// //           borderRadius: '50%',
// //           border: `1.5px solid ${color}`,
// //           opacity: 0,
// //           animation: `ringExpand 2.2s ease-out ${i * 0.55}s infinite`,
// //         }} />
// //       ))}
// //     </div>
// //   );
// // }

// // function EqualizerBars({ active, color }) {
// //   return (
// //     <div style={{
// //       display: 'flex', alignItems: 'center', justifyContent: 'center',
// //       gap: '3px', height: '36px',
// //       opacity: active ? 1 : 0.12,
// //       transition: 'opacity 0.4s ease',
// //     }}>
// //       {Array.from({ length: 20 }).map((_, i) => (
// //         <div key={i} style={{
// //           width: '3px', borderRadius: '2px',
// //           background: color,
// //           boxShadow: active ? `0 0 6px ${color}88` : 'none',
// //           height: '6px',
// //           animation: active ? `eqBar 0.${4 + (i % 5)}s ease-in-out ${i * 0.04}s infinite alternate` : 'none',
// //         }} />
// //       ))}
// //     </div>
// //   );
// // }

// // function MicWave({ active }) {
// //   return (
// //     <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', height: '30px' }}>
// //       {Array.from({ length: 14 }).map((_, i) => (
// //         <div key={i} style={{
// //           width: '3px', borderRadius: '2px',
// //           background: '#f43f5e',
// //           boxShadow: active ? '0 0 6px #f43f5e88' : 'none',
// //           height: active ? `${6 + (i % 5) * 5}px` : '5px',
// //           animation: active ? `eqBar 0.${3 + (i % 4)}s ease-in-out ${i * 0.05}s infinite alternate` : 'none',
// //           opacity: active ? 1 : 0.18,
// //           transition: 'all 0.2s',
// //         }} />
// //       ))}
// //     </div>
// //   );
// // }

// // function StatusPill({ label, color, pulse }) {
// //   return (
// //     <div style={{
// //       display: 'inline-flex', alignItems: 'center', gap: '7px',
// //       padding: '5px 16px', borderRadius: '100px',
// //       background: `${color}12`, border: `1px solid ${color}35`,
// //       fontFamily: "'JetBrains Mono', monospace",
// //       fontSize: '11px', fontWeight: 600, color, letterSpacing: '0.07em',
// //     }}>
// //       <div style={{
// //         width: '7px', height: '7px', borderRadius: '50%',
// //         background: color, boxShadow: `0 0 8px ${color}`,
// //         animation: pulse ? 'dotPulse 1s ease-in-out infinite' : 'none',
// //       }} />
// //       {label}
// //     </div>
// //   );
// // }

// // function TranscriptBubble({ text, role }) {
// //   if (!text) return null;
// //   const isUser = role === 'user';
// //   return (
// //     <div style={{
// //       padding: '9px 13px',
// //       borderRadius: isUser ? '14px 14px 3px 14px' : '3px 14px 14px 14px',
// //       background: isUser ? 'rgba(244,63,94,0.1)' : 'rgba(56,189,248,0.07)',
// //       border: `1px solid ${isUser ? 'rgba(244,63,94,0.22)' : 'rgba(56,189,248,0.18)'}`,
// //       color: isUser ? '#fda4af' : '#bae6fd',
// //       fontSize: '12.5px', lineHeight: '1.6',
// //       fontFamily: "'Syne', sans-serif",
// //       wordBreak: 'break-word',
// //       animation: 'fadeSlideIn 0.25s ease',
// //     }}>
// //       <span style={{ fontSize: '9px', opacity: 0.5, display: 'block', marginBottom: '3px', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.06em' }}>
// //         {isUser ? '👤 YOU' : '🤖 DOIT-AI'}
// //       </span>
// //       {text}
// //     </div>
// //   );
// // }

// // function ConversationLog({ turns }) {
// //   const logRef = useRef(null);
// //   useEffect(() => {
// //     logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
// //   }, [turns]);
// //   if (!turns.length) return null;
// //   return (
// //     <div ref={logRef} style={{
// //       width: '100%', maxHeight: '150px', overflowY: 'auto',
// //       display: 'flex', flexDirection: 'column', gap: '8px',
// //       padding: '0 1px',
// //       scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.08) transparent',
// //     }}>
// //       {turns.slice(-5).map((t, i) => (
// //         <TranscriptBubble key={i} text={t.text} role={t.role} />
// //       ))}
// //     </div>
// //   );
// // }

// // /* ═══════════════════════════════════════════════════════════════════════════
// //    MAIN COMPONENT
// //    ═══════════════════════════════════════════════════════════════════════════ */
// // const AIChatbot = ({ user }) => {
// //   const [isOpen, setIsOpen] = useState(false);
// //   const [mode, setMode] = useState('idle');
// //   // mode: 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
// //   const [expression, setExpression] = useState('idle');
// //   const [statusLabel, setStatusLabel] = useState('Tap mic to speak');
// //   const [transcript, setTranscript] = useState('');
// //   const [botText, setBotText] = useState('');
// //   const [turns, setTurns] = useState([]);
// //   const [errorMsg, setErrorMsg] = useState('');
// //   const [hasUnread, setHasUnread] = useState(false);

// //   const mediaRecorderRef = useRef(null);
// //   const audioChunksRef = useRef([]);
// //   const exprTimer = useRef(null);
// //   const audioRef = useRef(null);

// //   /* ── Color per mode ────────────────────────────────────────────── */
// //   const modeColor = {
// //     idle: '#38bdf8',
// //     listening: '#f43f5e',
// //     processing: '#f59e0b',
// //     speaking: '#10b981',
// //     error: '#ef4444',
// //   }[mode] || '#38bdf8';

// //   /* ── Expression helper ────────────────────────────────────────── */
// //   const setExpr = useCallback((expr, ttl) => {
// //     clearTimeout(exprTimer.current);
// //     setExpression(expr);
// //     if (ttl) exprTimer.current = setTimeout(() => setExpression('idle'), ttl);
// //   }, []);

// //   /* ── Start recording ─────────────────────────────────────────── */
// //   const startRecording = useCallback(async () => {
// //     try {
// //       const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
// //       const mimeType = MediaRecorder.isTypeSupported('audio/webm') 
// //         ? 'audio/webm' 
// //         : 'audio/mp4';
      
// //       const mediaRecorder = new MediaRecorder(stream, { mimeType });
// //       mediaRecorderRef.current = mediaRecorder;
// //       audioChunksRef.current = [];

// //       mediaRecorder.ondataavailable = (event) => {
// //         if (event.data.size > 0) {
// //           audioChunksRef.current.push(event.data);
// //         }
// //       };

// //       mediaRecorder.onstop = async () => {
// //         const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
// //         console.log(`🎤 Recorded audio: ${audioBlob.size} bytes`);
        
// //         // Stop media stream
// //         stream.getTracks().forEach(track => track.stop());
        
// //         // Send to backend
// //         await sendAudioToBackend(audioBlob);
// //       };

// //       mediaRecorder.start();
// //       setMode('listening');
// //       setExpr('listening');
// //       setStatusLabel('Listening… speak now');
// //       console.log('🎤 Recording started');
// //     } catch (err) {
// //       console.error('Microphone error:', err);
// //       setErrorMsg('Microphone access denied');
// //       setMode('error');
// //       setExpr('error', 3000);
// //       setTimeout(() => {
// //         setMode('idle');
// //         setStatusLabel('Tap mic to speak');
// //       }, 3500);
// //     }
// //   }, [setExpr]);

// //   /* ── Stop recording ──────────────────────────────────────────── */
// //   const stopRecording = useCallback(() => {
// //     if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
// //       mediaRecorderRef.current.stop();
// //       console.log('🎤 Recording stopped');
// //     }
// //   }, []);

// //   /* ── Send audio to backend using API service ─────────────────── */
// //   const sendAudioToBackend = async (audioBlob) => {
// //     setMode('processing');
// //     setExpr('thinking');
// //     setStatusLabel('Processing…');

// //     try {
// //       console.log('📤 Sending audio to voice chat API');

// //       // Use the voiceChatAPI service from api.js
// //       const result = await voiceChatAPI.chat(
// //         audioBlob,
// //         'friendly',  // persona
// //         turns.map(t => ({
// //           role: t.role === 'user' ? 'user' : 'assistant',
// //           content: t.text
// //         }))
// //       );

// //       console.log('✅ User said:', result.transcript);
// //       console.log('✅ Bot responds:', result.responseText);

// //       // Add to conversation
// //       setTurns(prev => [
// //         ...prev,
// //         { role: 'user', text: result.transcript },
// //         { role: 'bot', text: result.responseText }
// //       ]);

// //       // Play audio
// //       setMode('speaking');
// //       setExpr('speaking');
// //       setStatusLabel('Speaking…');
// //       setBotText(result.responseText);

// //       const audioUrl = URL.createObjectURL(result.audioBlob);
// //       const audio = new Audio(audioUrl);
// //       audioRef.current = audio;

// //       audio.onended = () => {
// //         setMode('idle');
// //         setExpr('happy', 2500);
// //         setStatusLabel('Tap mic to speak');
// //         setBotText('');
// //         if (!isOpen) setHasUnread(true);
// //         URL.revokeObjectURL(audioUrl);
// //       };

// //       audio.onerror = (e) => {
// //         console.error('Audio playback error:', e);
// //         setMode('error');
// //         setExpr('error', 3000);
// //         setStatusLabel('Playback failed');
// //         setTimeout(() => {
// //           setMode('idle');
// //           setStatusLabel('Tap mic to speak');
// //         }, 3500);
// //         URL.revokeObjectURL(audioUrl);
// //       };

// //       audio.play();

// //     } catch (err) {
// //       console.error('Voice chat error:', err);
// //       setErrorMsg(err.message || 'Voice chat failed');
// //       setMode('error');
// //       setExpr('error', 3500);
// //       setStatusLabel('Error — tap to retry');
// //       setTimeout(() => {
// //         setMode('idle');
// //         setStatusLabel('Tap mic to speak');
// //         setErrorMsg('');
// //       }, 4500);
// //     }
// //   };

// //   /* ── Stop all ────────────────────────────────────────────────── */
// //   const stopAll = useCallback(() => {
// //     if (mediaRecorderRef.current) {
// //       try {
// //         mediaRecorderRef.current.stop();
// //       } catch (e) {}
// //     }
// //     if (audioRef.current) {
// //       audioRef.current.pause();
// //       audioRef.current = null;
// //     }
// //     clearTimeout(exprTimer.current);
// //     setMode('idle');
// //     setExpression('idle');
// //     setStatusLabel('Tap mic to speak');
// //     setTranscript('');
// //     setBotText('');
// //   }, []);

// //   /* ── Toggle popup ────────────────────────────────────────────── */
// //   const toggleOpen = useCallback(() => {
// //     setIsOpen(prev => {
// //       const next = !prev;
// //       if (next) {
// //         setHasUnread(false);
// //         setExpr('happy', 1800);
// //         setStatusLabel('Tap mic to speak');
// //       } else {
// //         stopAll();
// //       }
// //       return next;
// //     });
// //   }, [stopAll, setExpr]);

// //   /* ── Mic button handler ──────────────────────────────────────── */
// //   const handleMicPress = () => {
// //     if (mode === 'listening') { stopRecording(); return; }
// //     if (mode === 'speaking') { stopAll(); return; }
// //     if (mode === 'processing') return;
// //     startRecording();
// //   };

// //   /* ── Cleanup ─────────────────────────────────────────────────── */
// //   useEffect(() => () => stopAll(), [stopAll]);

// //   /* ── Mic button appearance per mode ─────────────────────────── */
// //   const MicIconSVG = () => (
// //     <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
// //       <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
// //       <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
// //       <line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
// //     </svg>
// //   );
// //   const StopIconSVG = () => (
// //     <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
// //       <rect x="4" y="4" width="16" height="16" rx="3"/>
// //     </svg>
// //   );
// //   const SpinnerSVG = () => (
// //     <div style={{ width: '22px', height: '22px', border: '2px solid transparent', borderTopColor: '#f59e0b', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
// //   );

// //   const micCfg = {
// //     idle: { icon: <MicIconSVG />, label: 'SPEAK', color: '#38bdf8', bg: 'rgba(56,189,248,0.1)', border: 'rgba(56,189,248,0.3)' },
// //     listening: { icon: <StopIconSVG />, label: 'STOP', color: '#f43f5e', bg: 'rgba(244,63,94,0.12)', border: 'rgba(244,63,94,0.35)' },
// //     processing: { icon: <SpinnerSVG />, label: 'WAIT', color: '#f59e0b', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)' },
// //     speaking: { icon: <StopIconSVG />, label: 'STOP', color: '#10b981', bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)' },
// //     error: { icon: <MicIconSVG />, label: 'RETRY', color: '#ef4444', bg: 'rgba(239,68,68,0.1)', border: 'rgba(239,68,68,0.3)' },
// //   }[mode];

// //   /* ─────────────────────────────────────────────────────────────────
// //      RENDER
// //   ────────────────────────────────────────────────────────────────── */
// //   return (
// //     <>
// //       {/* Global keyframes + font */}
// //       <style>{`
// //         @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

// //         @keyframes robotFloat {
// //           0%, 100% { transform: translateY(0px); }
// //           50% { transform: translateY(-7px); }
// //         }
// //         @keyframes ringExpand {
// //           0% { transform: scale(0.45); opacity: 0.8; }
// //           100% { transform: scale(1.7); opacity: 0; }
// //         }
// //         @keyframes eqBar {
// //           0% { height: 5px; }
// //           100% { height: 30px; }
// //         }
// //         @keyframes dotPulse {
// //           0%, 100% { opacity: 1; box-shadow: 0 0 10px currentColor; }
// //           50% { opacity: 0.4; box-shadow: 0 0 3px currentColor; }
// //         }
// //         @keyframes ping {
// //           0% { transform: scale(1); opacity: 0.9; }
// //           80% { transform: scale(2.4); opacity: 0; }
// //           100% { transform: scale(2.8); opacity: 0; }
// //         }
// //         @keyframes popupIn {
// //           from { opacity: 0; transform: translateY(18px) scale(0.93); }
// //           to { opacity: 1; transform: translateY(0) scale(1); }
// //         }
// //         @keyframes fadeSlideIn {
// //           from { opacity: 0; transform: translateY(8px); }
// //           to { opacity: 1; transform: translateY(0); }
// //         }
// //         @keyframes spin { to { transform: rotate(360deg); } }

// //         .doit-log-scroll::-webkit-scrollbar { width: 3px; }
// //         .doit-log-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }

// //         .doit-mic-btn {
// //           transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease !important;
// //         }
// //         .doit-mic-btn:hover:not(:disabled) {
// //           transform: scale(1.07) !important;
// //           filter: brightness(1.18) !important;
// //         }
// //         .doit-mic-btn:active:not(:disabled) {
// //           transform: scale(0.95) !important;
// //         }

// //         .doit-float-btn:hover { filter: brightness(1.1); }
// //       `}</style>

// //       {/* FLOATING ROBOT ICON */}
// //       <button
// //         className="doit-float-btn"
// //         onClick={toggleOpen}
// //         title="DOIT-AI Voice Assistant"
// //         aria-label="Open DOIT AI Voice Assistant"
// //         style={{
// //           position: 'fixed', bottom: '24px', right: '24px',
// //           width: '84px', height: '84px',
// //           borderRadius: '50%', border: 'none',
// //           background: 'transparent', cursor: 'pointer',
// //           padding: 0, zIndex: 1001, outline: 'none',
// //           animation: 'robotFloat 3.8s ease-in-out infinite',
// //           transition: 'filter 0.2s ease',
// //         }}
// //       >
// //         <RobotSphere
// //           expression={isOpen ? 'happy' : expression}
// //           size={84}
// //           glowColor={modeColor}
// //           pulsing={mode === 'listening' || mode === 'speaking'}
// //         />
// //         {hasUnread && !isOpen && (
// //           <span style={{
// //             position: 'absolute', top: '6px', right: '6px',
// //             width: '13px', height: '13px',
// //             background: '#f43f5e', borderRadius: '50%',
// //             border: '2px solid #0c0f1a',
// //             animation: 'ping 1.3s ease infinite',
// //           }} />
// //         )}
// //       </button>

// //       {/* VOICE POPUP */}
// //       {isOpen && (
// //         <div style={{
// //           position: 'fixed',
// //           bottom: '120px', right: '20px',
// //           width: '340px',
// //           maxWidth: 'calc(100vw - 40px)',
// //           borderRadius: '24px',
// //           overflow: 'hidden',
// //           background: 'linear-gradient(165deg, #08101f 0%, #0d1529 40%, #111e38 100%)',
// //           border: '1px solid rgba(56,189,248,0.15)',
// //           boxShadow: `
// //             0 40px 90px rgba(0,0,0,0.75),
// //             0 0 0 1px rgba(255,255,255,0.04),
// //             inset 0 1px 0 rgba(255,255,255,0.06),
// //             0 0 80px ${modeColor}0a
// //           `,
// //           zIndex: 1000,
// //           animation: 'popupIn 0.3s cubic-bezier(0.34,1.4,0.64,1)',
// //           fontFamily: "'Syne', sans-serif",
// //           transition: 'box-shadow 0.5s ease',
// //         }}>

// //           {/* Header */}
// //           <div style={{
// //             display: 'flex', alignItems: 'center', gap: '12px',
// //             padding: '14px 16px 10px',
// //             borderBottom: '1px solid rgba(255,255,255,0.045)',
// //             background: 'rgba(0,0,0,0.2)',
// //           }}>
// //             <RobotSphere expression={expression} size={38} glowColor={modeColor} />
// //             <div style={{ flex: 1 }}>
// //               <div style={{ fontSize: '14px', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em' }}>
// //                 DOIT-AI
// //               </div>
// //               <div style={{ fontSize: '9.5px', color: '#334155', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.1em', marginTop: '1px' }}>
// //                 AZURE WHISPER + TTS · GPT-4O-MINI
// //               </div>
// //             </div>
// //             <button
// //               onClick={toggleOpen}
// //               style={{
// //                 background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)',
// //                 borderRadius: '9px', width: '30px', height: '30px',
// //                 display: 'flex', alignItems: 'center', justifyContent: 'center',
// //                 cursor: 'pointer', color: '#475569', fontSize: '15px',
// //                 transition: 'all 0.15s', outline: 'none',
// //               }}
// //               onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.09)'; e.currentTarget.style.color = '#94a3b8'; }}
// //               onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#475569'; }}
// //             >✕</button>
// //           </div>

// //           {/* Body */}
// //           <div style={{ padding: '22px 18px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>

// //             {/* Large Robot with rings */}
// //             <div style={{ position: 'relative', width: '158px', height: '158px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
// //               <VoiceRings active={mode === 'listening'} color="#f43f5e" />
// //               <VoiceRings active={mode === 'speaking'} color="#10b981" />
// //               <RobotSphere
// //                 expression={expression}
// //                 size={148}
// //                 glowColor={modeColor}
// //                 pulsing={mode === 'listening' || mode === 'processing' || mode === 'speaking'}
// //               />
// //               {mode === 'processing' && (
// //                 <div style={{
// //                   position: 'absolute', inset: '4px', borderRadius: '50%',
// //                   border: '2px solid transparent',
// //                   borderTopColor: '#f59e0b',
// //                   borderRightColor: '#f59e0b33',
// //                   animation: 'spin 1.1s linear infinite',
// //                   pointerEvents: 'none',
// //                 }} />
// //               )}
// //             </div>

// //             {/* Status pill */}
// //             <StatusPill label={statusLabel} color={modeColor} pulse={mode !== 'idle'} />

// //             {/* Bot speaking equalizer */}
// //             <EqualizerBars active={mode === 'speaking'} color="#10b981" />

// //             {/* Mic waveform (listening) */}
// //             {mode === 'listening' && (
// //               <div style={{ width: '100%', animation: 'fadeSlideIn 0.2s ease' }}>
// //                 <MicWave active />
// //               </div>
// //             )}

// //             {/* Bot text while speaking */}
// //             {mode === 'speaking' && botText && (
// //               <div style={{
// //                 width: '100%', padding: '10px 14px', borderRadius: '12px',
// //                 background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.18)',
// //                 color: '#6ee7b7', fontSize: '12.5px', lineHeight: '1.65',
// //                 maxHeight: '82px', overflowY: 'auto',
// //                 animation: 'fadeSlideIn 0.3s ease',
// //               }}>
// //                 {botText}
// //               </div>
// //             )}

// //             {/* Error */}
// //             {mode === 'error' && errorMsg && (
// //               <div style={{
// //                 width: '100%', padding: '8px 12px', borderRadius: '10px',
// //                 background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.22)',
// //                 color: '#fca5a5', fontSize: '12px',
// //                 animation: 'fadeSlideIn 0.2s ease',
// //               }}>
// //                 ⚠ {errorMsg}
// //               </div>
// //             )}

// //             {/* Conversation log */}
// //             {turns.length > 0 && mode === 'idle' && (
// //               <div className="doit-log-scroll" style={{ width: '100%', animation: 'fadeSlideIn 0.3s ease' }}>
// //                 <div style={{
// //                   fontSize: '9px', fontFamily: "'JetBrains Mono', monospace",
// //                   color: '#1e3a5f', letterSpacing: '0.1em', textTransform: 'uppercase',
// //                   marginBottom: '8px',
// //                 }}>
// //                   Conversation
// //                 </div>
// //                 <ConversationLog turns={turns} />
// //               </div>
// //             )}

// //             {/* BIG MIC BUTTON */}
// //             <button
// //               className="doit-mic-btn"
// //               onClick={handleMicPress}
// //               disabled={mode === 'processing'}
// //               aria-label={micCfg.label}
// //               style={{
// //                 width: '76px', height: '76px', borderRadius: '50%',
// //                 border: `2px solid ${micCfg.border}`,
// //                 background: micCfg.bg, color: micCfg.color,
// //                 cursor: mode === 'processing' ? 'not-allowed' : 'pointer',
// //                 display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
// //                 gap: '4px',
// //                 boxShadow: `0 0 28px ${micCfg.color}20, inset 0 1px 0 rgba(255,255,255,0.06)`,
// //                 outline: 'none',
// //                 animation: mode === 'listening' ? 'dotPulse 1.2s ease infinite' : 'none',
// //               }}
// //             >
// //               {micCfg.icon}
// //               <span style={{
// //                 fontSize: '8.5px', fontFamily: "'JetBrains Mono', monospace",
// //                 fontWeight: 700, letterSpacing: '0.1em',
// //               }}>
// //                 {micCfg.label}
// //               </span>
// //             </button>

// //             {/* Reset conversation */}
// //             {turns.length > 0 && (
// //               <button
// //                 onClick={() => { stopAll(); setTurns([]); setErrorMsg(''); }}
// //                 style={{
// //                   background: 'none', border: 'none',
// //                   color: '#1e3a5f', fontSize: '10.5px',
// //                   fontFamily: "'JetBrains Mono', monospace",
// //                   cursor: 'pointer', letterSpacing: '0.04em',
// //                   padding: '3px 8px', borderRadius: '6px',
// //                   transition: 'color 0.15s', outline: 'none',
// //                 }}
// //                 onMouseEnter={e => e.currentTarget.style.color = '#475569'}
// //                 onMouseLeave={e => e.currentTarget.style.color = '#1e3a5f'}
// //               >
// //                 ↺ New conversation
// //               </button>
// //             )}
// //           </div>

// //           {/* Footer */}
// //           <div style={{
// //             padding: '7px 16px 10px',
// //             borderTop: '1px solid rgba(255,255,255,0.035)',
// //             textAlign: 'center',
// //             fontSize: '9px', fontFamily: "'JetBrains Mono', monospace",
// //             color: '#0f2035', letterSpacing: '0.07em',
// //           }}>
// //             DOIT-AI · Azure Whisper STT + TTS · Backend Processing
// //           </div>
// //         </div>
// //       )}
// //     </>
// //   );
// // };

// // export default AIChatbot;
// import React, { useState, useRef, useEffect, useCallback } from 'react';

// /* ═══════════════════════════════════════════════════════════════════════════
//    DOIT-BOT · Azure AI Foundry Voice Live Agent (Agent905)
//    Glass Sphere LED Robot → Click to activate → Speak → Agent replies in voice

//    ARCHITECTURE:
//    - Browser MediaRecorder captures mic audio (PCM via AudioWorklet)
//    - WebSocket connects to backend proxy → Azure VoiceLive WSS
//    - Streams audio to Agent905 (gpt-4o-realtime-preview)
//    - Streams audio response back → plays via AudioContext
//    - Server VAD handles turn detection automatically

//    BACKEND PROXY EXPECTED ENDPOINT:
//      WS  /api/foundry-agent/voice-live   (forwards to Azure VoiceLive)
//      GET /api/foundry-agent/health        (health check)
//    ═══════════════════════════════════════════════════════════════════════════ */

// const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';
// const WS_BASE_URL  = API_BASE_URL.replace(/^http/, 'ws');

// /* ─── LED dot-matrix definitions ──────────────────────────────────────────── */
// const GAP = 10, OX = 22, OY = 52, DOT = 4.2;

// const EXPRESSIONS = {
//   idle: {
//     leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
//     rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
//     mouth:    [[4,3],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,3]],
//   },
//   listening: {
//     leftEye:  [[2,0],[3,0],[4,0],[5,0],[6,0]],
//     rightEye: [[10,0],[11,0],[12,0],[13,0],[14,0]],
//     mouth:    [[6,3],[7,3],[8,3],[9,3],[10,3]],
//   },
//   thinking: {
//     leftEye:  [[2,0],[3,1],[4,0],[5,1],[6,0]],
//     rightEye: [[10,0],[11,1],[12,0],[13,1],[14,0]],
//     mouth:    [[5,3],[6,3],[7,3],[9,3],[10,3],[11,3]],
//   },
//   speaking: {
//     leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
//     rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
//     mouth:    [[4,3],[5,3],[6,3],[7,3],[8,3],[9,3],[10,3],[11,3],
//                [4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4]],
//   },
//   happy: {
//     leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
//     rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
//     mouth:    [[3,3],[4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4],[12,3]],
//   },
//   error: {
//     leftEye:  [[2,0],[3,0],[4,1],[5,0],[6,0]],
//     rightEye: [[10,0],[11,0],[12,1],[13,0],[14,0]],
//     mouth:    [[4,4],[5,3],[6,3],[7,3],[8,3],[9,3],[10,3],[11,4]],
//   },
// };

// /* ─── SVG Components ──────────────────────────────────────────────────────── */
// function LedFace({ expression = 'idle', glowColor = '#38bdf8' }) {
//   const expr = EXPRESSIONS[expression] || EXPRESSIONS.idle;
//   const dots = [...expr.leftEye, ...expr.rightEye, ...expr.mouth];
//   return (
//     <>
//       {dots.map(([gx, gy], i) => (
//         <circle
//           key={i}
//           cx={OX + gx * GAP}
//           cy={OY + gy * GAP}
//           r={DOT}
//           fill={glowColor}
//           style={{
//             filter: `drop-shadow(0 0 5px ${glowColor}) drop-shadow(0 0 10px ${glowColor}88)`,
//             transition: 'all 0.12s ease',
//           }}
//         />
//       ))}
//     </>
//   );
// }

// function RobotSphere({ expression, size = 80, glowColor = '#38bdf8', pulsing = false }) {
//   const uid = `rs_${size}`;
//   return (
//     <svg
//       width={size} height={size}
//       viewBox="0 0 180 200"
//       xmlns="http://www.w3.org/2000/svg"
//       style={{
//         display: 'block',
//         filter: pulsing
//           ? `drop-shadow(0 0 18px ${glowColor}) drop-shadow(0 8px 24px ${glowColor}66)`
//           : `drop-shadow(0 8px 24px ${glowColor}44) drop-shadow(0 2px 8px rgba(0,0,0,0.5))`,
//         transition: 'filter 0.35s ease',
//       }}
//     >
//       <defs>
//         <linearGradient id={`chrome_${uid}`} x1="0" y1="0" x2="1" y2="1">
//           <stop offset="0%"   stopColor="#9ca3af" />
//           <stop offset="30%"  stopColor="#e5e7eb" />
//           <stop offset="60%"  stopColor="#6b7280" />
//           <stop offset="100%" stopColor="#374151" />
//         </linearGradient>
//         <radialGradient id={`sphere_${uid}`} cx="38%" cy="30%" r="65%">
//           <stop offset="0%"   stopColor="#1e293b" stopOpacity="0.7" />
//           <stop offset="60%"  stopColor="#0f172a" stopOpacity="0.92" />
//           <stop offset="100%" stopColor="#020617" />
//         </radialGradient>
//         <radialGradient id={`sheen_${uid}`} cx="30%" cy="22%" r="50%">
//           <stop offset="0%"   stopColor="white"   stopOpacity="0.3" />
//           <stop offset="100%" stopColor="white"   stopOpacity="0" />
//         </radialGradient>
//         <radialGradient id={`glow_${uid}`} cx="50%" cy="90%" r="50%">
//           <stop offset="0%"   stopColor={glowColor} stopOpacity="0.2" />
//           <stop offset="100%" stopColor={glowColor} stopOpacity="0" />
//         </radialGradient>
//         <radialGradient id={`cap_${uid}`} cx="35%" cy="30%" r="65%">
//           <stop offset="0%"   stopColor={glowColor} />
//           <stop offset="100%" stopColor={glowColor} stopOpacity="0.4" />
//         </radialGradient>
//         <linearGradient id={`ear_${uid}`} x1="0" y1="0" x2="1" y2="1">
//           <stop offset="0%"   stopColor="#374151" />
//           <stop offset="100%" stopColor="#111827" />
//         </linearGradient>
//       </defs>
//       <line x1="108" y1="8" x2="120" y2="30" stroke="#9ca3af" strokeWidth="2.5" strokeLinecap="round"/>
//       <circle cx="120" cy="28" r="5" fill={`url(#cap_${uid})`}
//         style={{ filter: `drop-shadow(0 0 6px ${glowColor})` }} />
//       <circle cx="90" cy="98" r="76" fill={`url(#chrome_${uid})`} />
//       <circle cx="90" cy="98" r="68" fill={`url(#sphere_${uid})`} />
//       <LedFace expression={expression} glowColor={glowColor} />
//       <ellipse cx="72"  cy="72" rx="46" ry="36" fill={`url(#sheen_${uid})`} />
//       <circle  cx="90"  cy="98" r="68"  fill={`url(#glow_${uid})`} />
//       <ellipse cx="16"  cy="98" rx="10" ry="14" fill={`url(#ear_${uid})`} stroke="#4b5563" strokeWidth="1"/>
//       <ellipse cx="16"  cy="98" rx="5"  ry="8"  fill={glowColor} opacity="0.25" />
//       <ellipse cx="164" cy="98" rx="10" ry="14" fill={`url(#ear_${uid})`} stroke="#4b5563" strokeWidth="1"/>
//       <ellipse cx="164" cy="98" rx="5"  ry="8"  fill={glowColor} opacity="0.25" />
//       <polygon points="74,170 88,163 88,177"  fill="#1e293b" stroke="#374151" strokeWidth="1"/>
//       <polygon points="106,170 92,163 92,177" fill="#1e293b" stroke="#374151" strokeWidth="1"/>
//       <ellipse cx="90"  cy="170" rx="6" ry="5"  fill="#374151" stroke="#4b5563" strokeWidth="1"/>
//     </svg>
//   );
// }

// function VoiceRings({ active, color }) {
//   if (!active) return null;
//   return (
//     <div style={{ position:'absolute', inset:0, pointerEvents:'none', display:'flex', alignItems:'center', justifyContent:'center' }}>
//       {[0,1,2].map(i => (
//         <div key={i} style={{
//           position: 'absolute',
//           width:  `${90 + i*38}px`, height: `${90 + i*38}px`,
//           borderRadius: '50%',
//           border: `1.5px solid ${color}`,
//           opacity: 0,
//           animation: `ringExpand 2.2s ease-out ${i*0.55}s infinite`,
//         }} />
//       ))}
//     </div>
//   );
// }

// function EqualizerBars({ active, color }) {
//   return (
//     <div style={{
//       display:'flex', alignItems:'center', justifyContent:'center',
//       gap:'3px', height:'36px',
//       opacity: active ? 1 : 0.12,
//       transition: 'opacity 0.4s ease',
//     }}>
//       {Array.from({ length: 20 }).map((_, i) => (
//         <div key={i} style={{
//           width: '3px', borderRadius: '2px',
//           background: color,
//           boxShadow: active ? `0 0 6px ${color}88` : 'none',
//           height: '6px',
//           animation: active ? `eqBar 0.${4+(i%5)}s ease-in-out ${i*0.04}s infinite alternate` : 'none',
//         }} />
//       ))}
//     </div>
//   );
// }

// function MicWave({ active }) {
//   return (
//     <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:'4px', height:'30px' }}>
//       {Array.from({ length: 14 }).map((_, i) => (
//         <div key={i} style={{
//           width: '3px', borderRadius: '2px',
//           background: '#f43f5e',
//           boxShadow: active ? '0 0 6px #f43f5e88' : 'none',
//           height: active ? `${6+(i%5)*5}px` : '5px',
//           animation: active ? `eqBar 0.${3+(i%4)}s ease-in-out ${i*0.05}s infinite alternate` : 'none',
//           opacity: active ? 1 : 0.18,
//           transition: 'all 0.2s',
//         }} />
//       ))}
//     </div>
//   );
// }

// function StatusPill({ label, color, pulse }) {
//   return (
//     <div style={{
//       display:'inline-flex', alignItems:'center', gap:'7px',
//       padding:'5px 16px', borderRadius:'100px',
//       background:`${color}12`, border:`1px solid ${color}35`,
//       fontFamily:"'JetBrains Mono', monospace",
//       fontSize:'11px', fontWeight:600, color, letterSpacing:'0.07em',
//     }}>
//       <div style={{
//         width:'7px', height:'7px', borderRadius:'50%',
//         background:color, boxShadow:`0 0 8px ${color}`,
//         animation: pulse ? 'dotPulse 1s ease-in-out infinite' : 'none',
//       }} />
//       {label}
//     </div>
//   );
// }

// function TranscriptBubble({ text, role }) {
//   if (!text) return null;
//   const isUser = role === 'user';
//   return (
//     <div style={{
//       padding:'9px 13px',
//       borderRadius: isUser ? '14px 14px 3px 14px' : '3px 14px 14px 14px',
//       background: isUser ? 'rgba(244,63,94,0.1)' : 'rgba(56,189,248,0.07)',
//       border: `1px solid ${isUser ? 'rgba(244,63,94,0.22)' : 'rgba(56,189,248,0.18)'}`,
//       color: isUser ? '#fda4af' : '#bae6fd',
//       fontSize:'12.5px', lineHeight:'1.6',
//       fontFamily:"'Syne', sans-serif",
//       wordBreak:'break-word',
//       animation:'fadeSlideIn 0.25s ease',
//     }}>
//       <span style={{ fontSize:'9px', opacity:0.5, display:'block', marginBottom:'3px', fontFamily:"'JetBrains Mono', monospace", letterSpacing:'0.06em' }}>
//         {isUser ? '👤 YOU' : '🤖 AGENT905'}
//       </span>
//       {text}
//     </div>
//   );
// }

// function ConversationLog({ turns }) {
//   const logRef = useRef(null);
//   useEffect(() => {
//     logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior:'smooth' });
//   }, [turns]);
//   if (!turns.length) return null;
//   return (
//     <div ref={logRef} style={{
//       width:'100%', maxHeight:'150px', overflowY:'auto',
//       display:'flex', flexDirection:'column', gap:'8px',
//       padding:'0 1px',
//       scrollbarWidth:'thin', scrollbarColor:'rgba(255,255,255,0.08) transparent',
//     }}>
//       {turns.slice(-5).map((t, i) => (
//         <TranscriptBubble key={i} text={t.text} role={t.role} />
//       ))}
//     </div>
//   );
// }

// /* ═══════════════════════════════════════════════════════════════════════════
//    PCM16 AudioWorklet processor (inlined as blob URL)
//    Converts Float32 mic input → Int16 PCM → base64 for VoiceLive
//    ═══════════════════════════════════════════════════════════════════════════ */
// const WORKLET_CODE = `
// class PCM16Processor extends AudioWorkletProcessor {
//   constructor() { super(); this._buf = []; }
//   process(inputs) {
//     const ch = inputs[0][0];
//     if (!ch) return true;
//     const i16 = new Int16Array(ch.length);
//     for (let i = 0; i < ch.length; i++) {
//       i16[i] = Math.max(-32768, Math.min(32767, ch[i] * 32768));
//     }
//     this.port.postMessage(i16.buffer, [i16.buffer]);
//     return true;
//   }
// }
// registerProcessor('pcm16-processor', PCM16Processor);
// `;

// function createWorkletURL() {
//   return URL.createObjectURL(new Blob([WORKLET_CODE], { type: 'application/javascript' }));
// }

// function arrayBufferToBase64(buf) {
//   const bytes = new Uint8Array(buf);
//   let bin = '';
//   for (let i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
//   return btoa(bin);
// }

// function base64ToArrayBuffer(b64) {
//   const bin = atob(b64);
//   const buf = new ArrayBuffer(bin.length);
//   const view = new Uint8Array(buf);
//   for (let i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
//   return buf;
// }

// /* ═══════════════════════════════════════════════════════════════════════════
//    VoiceLive WebSocket Manager
//    Wraps the connection to the backend proxy that forwards to Azure VoiceLive
//    ═══════════════════════════════════════════════════════════════════════════ */
// class VoiceLiveSession {
//   constructor({ wsUrl, token, tabKey, onEvent, onError, onClose }) {
//     this.wsUrl    = wsUrl;
//     this.token    = token;
//     this.tabKey   = tabKey;
//     this.onEvent  = onEvent;
//     this.onError  = onError;
//     this.onClose  = onClose;
//     this.ws       = null;
//     this.ready    = false;
//   }

//   connect() {
//     // Attach auth as query params (WS can't set headers in browser)
//     const url = `${this.wsUrl}?token=${encodeURIComponent(this.token)}&tab=${encodeURIComponent(this.tabKey)}`;
//     this.ws = new WebSocket(url);
//     this.ws.binaryType = 'arraybuffer';

//     this.ws.onopen = () => {
//       this.ready = true;
//       console.log('[VoiceLive] WebSocket connected');
//       // Send session config to backend proxy
//       this._send({ type: 'session.config', agent_id: 'Agent905' });
//     };

//     this.ws.onmessage = (ev) => {
//       try {
//         const event = typeof ev.data === 'string' ? JSON.parse(ev.data) : null;
//         if (event) this.onEvent(event);
//       } catch (e) {
//         console.warn('[VoiceLive] Parse error:', e);
//       }
//     };

//     this.ws.onerror = (e) => {
//       console.error('[VoiceLive] WebSocket error:', e);
//       this.onError(e);
//     };

//     this.ws.onclose = (e) => {
//       this.ready = false;
//       console.log('[VoiceLive] WebSocket closed', e.code);
//       this.onClose(e);
//     };
//   }

//   sendAudio(base64Pcm16) {
//     if (this.ready && this.ws?.readyState === WebSocket.OPEN) {
//       this._send({ type: 'input_audio_buffer.append', audio: base64Pcm16 });
//     }
//   }

//   cancelResponse() {
//     if (this.ready) this._send({ type: 'response.cancel' });
//   }

//   disconnect() {
//     this.ready = false;
//     if (this.ws) { try { this.ws.close(); } catch(e){} this.ws = null; }
//   }

//   _send(obj) {
//     if (this.ws?.readyState === WebSocket.OPEN) {
//       this.ws.send(JSON.stringify(obj));
//     }
//   }
// }

// /* ═══════════════════════════════════════════════════════════════════════════
//    PCM16 Playback Queue
//    Decodes streamed PCM16 audio and plays it immediately via AudioContext
//    ═══════════════════════════════════════════════════════════════════════════ */
// class AudioPlaybackQueue {
//   constructor() {
//     this.ctx       = null;
//     this.queue     = [];
//     this.nextStart = 0;
//     this.active    = false;
//   }

//   _ensureCtx() {
//     if (!this.ctx || this.ctx.state === 'closed') {
//       this.ctx       = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
//       this.nextStart = 0;
//     }
//     if (this.ctx.state === 'suspended') this.ctx.resume();
//   }

//   push(base64Pcm16) {
//     this._ensureCtx();
//     const raw  = base64ToArrayBuffer(base64Pcm16);
//     const i16  = new Int16Array(raw);
//     const f32  = new Float32Array(i16.length);
//     for (let i = 0; i < i16.length; i++) f32[i] = i16[i] / 32768;

//     const buf = this.ctx.createBuffer(1, f32.length, 24000);
//     buf.copyToChannel(f32, 0);

//     const src = this.ctx.createBufferSource();
//     src.buffer = buf;
//     src.connect(this.ctx.destination);

//     const now  = this.ctx.currentTime;
//     const when = Math.max(now, this.nextStart);
//     src.start(when);
//     this.nextStart = when + buf.duration;
//     this.active    = true;

//     src.onended = () => {
//       if (this.nextStart <= this.ctx.currentTime + 0.01) this.active = false;
//     };
//   }

//   stop() {
//     if (this.ctx) { try { this.ctx.close(); } catch(e){} }
//     this.ctx       = null;
//     this.nextStart = 0;
//     this.active    = false;
//   }

//   isPlaying() { return this.active; }
// }

// /* ═══════════════════════════════════════════════════════════════════════════
//    MAIN COMPONENT
//    ═══════════════════════════════════════════════════════════════════════════ */
// const AIChatbot = ({ user }) => {
//   const [isOpen,      setIsOpen]      = useState(false);
//   const [mode,        setMode]        = useState('idle');
//   // mode: 'idle' | 'connecting' | 'listening' | 'processing' | 'speaking' | 'error'
//   const [expression,  setExpression]  = useState('idle');
//   const [statusLabel, setStatusLabel] = useState('Tap to connect');
//   const [botText,     setBotText]     = useState('');
//   const [turns,       setTurns]       = useState([]);
//   const [errorMsg,    setErrorMsg]    = useState('');
//   const [hasUnread,   setHasUnread]   = useState(false);
//   const [connected,   setConnected]   = useState(false);

//   const sessionRef   = useRef(null);  // VoiceLiveSession
//   const playbackRef  = useRef(null);  // AudioPlaybackQueue
//   const audioCtxRef  = useRef(null);  // AudioContext for capture
//   const workletRef   = useRef(null);  // AudioWorkletNode
//   const streamRef    = useRef(null);  // MediaStream
//   const workletURL   = useRef(null);
//   const exprTimer    = useRef(null);
//   const agentTextBuf = useRef('');
//   const userTextBuf  = useRef('');

//   /* ── Color per mode ─────────────────────────────────────────────── */
//   const modeColor = {
//     idle:       '#38bdf8',
//     connecting: '#f59e0b',
//     listening:  '#f43f5e',
//     processing: '#f59e0b',
//     speaking:   '#10b981',
//     error:      '#ef4444',
//   }[mode] || '#38bdf8';

//   /* ── Expression helper ──────────────────────────────────────────── */
//   const setExpr = useCallback((expr, ttl) => {
//     clearTimeout(exprTimer.current);
//     setExpression(expr);
//     if (ttl) exprTimer.current = setTimeout(() => setExpression('idle'), ttl);
//   }, []);

//   /* ── Handle VoiceLive events ────────────────────────────────────── */
//   const handleEvent = useCallback((event) => {
//     const t = event.type;
//     console.log('[VoiceLive Event]', t);

//     if (t === 'session.updated') {
//       console.log('[VoiceLive] Session ready:', event.session?.id);
//       setConnected(true);
//       setMode('listening');
//       setExpr('listening');
//       setStatusLabel('Listening — speak now');
//     }

//     else if (t === 'input_audio_buffer.speech_started') {
//       console.log('[VoiceLive] User speaking detected');
//       // Interrupt any agent speech
//       playbackRef.current?.stop();
//       playbackRef.current = new AudioPlaybackQueue();
//       // Cancel ongoing response
//       sessionRef.current?.cancelResponse();
//       agentTextBuf.current = '';
//       setBotText('');
//       setMode('listening');
//       setExpr('listening');
//       setStatusLabel('Listening…');
//     }

//     else if (t === 'input_audio_buffer.speech_stopped') {
//       setMode('processing');
//       setExpr('thinking');
//       setStatusLabel('Processing…');
//       // Flush user transcript
//       if (userTextBuf.current.trim()) {
//         setTurns(prev => [...prev, { role: 'user', text: userTextBuf.current.trim() }]);
//         userTextBuf.current = '';
//       }
//     }

//     else if (t === 'conversation.item.input_audio_transcription.completed') {
//       userTextBuf.current = event.transcript || '';
//     }

//     else if (t === 'response.created') {
//       agentTextBuf.current = '';
//       setMode('speaking');
//       setExpr('speaking');
//       setStatusLabel('Agent905 speaking…');
//     }

//     else if (t === 'response.audio.delta') {
//       if (event.delta) {
//         playbackRef.current = playbackRef.current || new AudioPlaybackQueue();
//         playbackRef.current.push(event.delta);
//       }
//     }

//     else if (t === 'response.audio_transcript.delta') {
//       agentTextBuf.current += (event.delta || '');
//       setBotText(agentTextBuf.current);
//     }

//     else if (t === 'response.audio.done') {
//       console.log('[VoiceLive] Agent finished speaking');
//     }

//     else if (t === 'response.done') {
//       const finalText = agentTextBuf.current.trim();
//       if (finalText) {
//         setTurns(prev => [...prev, { role: 'bot', text: finalText }]);
//       }
//       agentTextBuf.current = '';
//       setBotText('');
//       setMode('listening');
//       setExpr('happy', 2000);
//       setStatusLabel('Listening — speak now');
//       if (!isOpen) setHasUnread(true);
//     }

//     else if (t === 'error') {
//       const msg = event.error?.message || 'VoiceLive error';
//       console.error('[VoiceLive] Error event:', msg);
//       setErrorMsg(msg);
//       setMode('error');
//       setExpr('error', 3000);
//       setStatusLabel('Error — tap to reconnect');
//     }
//   }, [isOpen, setExpr]);

//   /* ── Start microphone capture → PCM16 → WebSocket ──────────────── */
//   const startMicCapture = useCallback(async () => {
//     try {
//       const stream = await navigator.mediaDevices.getUserMedia({
//         audio: { sampleRate: 24000, channelCount: 1, echoCancellation: true, noiseSuppression: true }
//       });
//       streamRef.current = stream;

//       const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
//       audioCtxRef.current = ctx;

//       if (!workletURL.current) workletURL.current = createWorkletURL();
//       await ctx.audioWorklet.addModule(workletURL.current);

//       const source   = ctx.createMediaStreamSource(stream);
//       const worklet  = new AudioWorkletNode(ctx, 'pcm16-processor');
//       workletRef.current = worklet;

//       worklet.port.onmessage = (ev) => {
//         const base64 = arrayBufferToBase64(ev.data);
//         sessionRef.current?.sendAudio(base64);
//       };

//       source.connect(worklet);
//       console.log('[Mic] PCM16 capture started at 24kHz');
//     } catch (err) {
//       console.error('[Mic] Failed to start capture:', err);
//       throw err;
//     }
//   }, []);

//   /* ── Stop microphone capture ────────────────────────────────────── */
//   const stopMicCapture = useCallback(() => {
//     if (workletRef.current) {
//       try { workletRef.current.disconnect(); } catch(e){}
//       workletRef.current = null;
//     }
//     if (audioCtxRef.current) {
//       try { audioCtxRef.current.close(); } catch(e){}
//       audioCtxRef.current = null;
//     }
//     if (streamRef.current) {
//       streamRef.current.getTracks().forEach(t => t.stop());
//       streamRef.current = null;
//     }
//   }, []);

//   /* ── Connect to Azure AI Foundry Voice Live ─────────────────────── */
//   const connect = useCallback(async () => {
//     setMode('connecting');
//     setExpr('thinking');
//     setStatusLabel('Connecting to Agent905…');
//     setErrorMsg('');

//     try {
//       const token  = localStorage.getItem('token') || '';
//       const tabKey = sessionStorage.getItem('tab_session_key') || '';

//       const session = new VoiceLiveSession({
//         wsUrl:   `${WS_BASE_URL}/api/foundry-agent/voice-live`,
//         token,
//         tabKey,
//         onEvent: handleEvent,
//         onError: (e) => {
//           setErrorMsg('WebSocket connection failed');
//           setMode('error');
//           setExpr('error', 3000);
//           setStatusLabel('Connection failed — tap to retry');
//         },
//         onClose: (e) => {
//           if (e.code !== 1000) {
//             setConnected(false);
//             setMode('idle');
//             setExpr('idle');
//             setStatusLabel('Disconnected — tap to reconnect');
//           }
//         },
//       });

//       sessionRef.current = session;
//       session.connect();

//       // Start mic capture in parallel
//       await startMicCapture();

//     } catch (err) {
//       console.error('[Connect] Error:', err);
//       setErrorMsg(err.message || 'Connection failed');
//       setMode('error');
//       setExpr('error', 3000);
//       setStatusLabel('Error — tap to retry');
//       setTimeout(() => {
//         if (!connected) { setMode('idle'); setStatusLabel('Tap to connect'); }
//       }, 4000);
//     }
//   }, [handleEvent, startMicCapture, connected]);

//   /* ── Disconnect ─────────────────────────────────────────────────── */
//   const disconnect = useCallback(() => {
//     sessionRef.current?.disconnect();
//     sessionRef.current = null;
//     stopMicCapture();
//     playbackRef.current?.stop();
//     playbackRef.current = null;
//     setConnected(false);
//     setMode('idle');
//     setExpr('idle');
//     setStatusLabel('Tap to connect');
//     setBotText('');
//     agentTextBuf.current = '';
//     userTextBuf.current  = '';
//   }, [stopMicCapture, setExpr]);

//   /* ── Toggle popup ────────────────────────────────────────────────── */
//   const toggleOpen = useCallback(() => {
//     setIsOpen(prev => {
//       const next = !prev;
//       if (next) {
//         setHasUnread(false);
//         setExpr('happy', 1800);
//       } else {
//         disconnect();
//       }
//       return next;
//     });
//   }, [disconnect, setExpr]);

//   /* ── Main button handler ─────────────────────────────────────────── */
//   const handleMainButton = () => {
//     if (mode === 'connecting' || mode === 'processing') return;
//     if (connected) {
//       disconnect();
//     } else {
//       connect();
//     }
//   };

//   /* ── Cleanup ─────────────────────────────────────────────────────── */
//   useEffect(() => () => {
//     disconnect();
//     if (workletURL.current) URL.revokeObjectURL(workletURL.current);
//   }, [disconnect]);

//   /* ── Button config ───────────────────────────────────────────────── */
//   const ConnectIcon = () => (
//     <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
//       <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
//       <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
//       <line x1="12" y1="19" x2="12" y2="23"/>
//       <line x1="8" y1="23" x2="16" y2="23"/>
//     </svg>
//   );
//   const DisconnectIcon = () => (
//     <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
//       <rect x="4" y="4" width="16" height="16" rx="3"/>
//     </svg>
//   );
//   const SpinnerSVG = () => (
//     <div style={{ width:'22px', height:'22px', border:'2px solid transparent', borderTopColor:'#f59e0b', borderRadius:'50%', animation:'spin 0.7s linear infinite' }} />
//   );

//   const btnCfg = connected
//     ? { icon: <DisconnectIcon />, label: 'STOP',    color:'#ef4444', bg:'rgba(239,68,68,0.1)',    border:'rgba(239,68,68,0.3)' }
//     : mode === 'connecting' || mode === 'processing'
//       ? { icon: <SpinnerSVG />,    label: 'WAIT',    color:'#f59e0b', bg:'rgba(245,158,11,0.08)',  border:'rgba(245,158,11,0.25)' }
//       : mode === 'error'
//         ? { icon: <ConnectIcon />, label: 'RETRY',   color:'#ef4444', bg:'rgba(239,68,68,0.1)',    border:'rgba(239,68,68,0.3)' }
//         : { icon: <ConnectIcon />, label: 'CONNECT', color:'#38bdf8', bg:'rgba(56,189,248,0.1)',   border:'rgba(56,189,248,0.3)' };

//   /* ─────────────────────────────────────────────────────────────────
//      RENDER
//   ────────────────────────────────────────────────────────────────── */
//   return (
//     <>
//       <style>{`
//         @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

//         @keyframes robotFloat {
//           0%, 100% { transform: translateY(0px); }
//           50%       { transform: translateY(-7px); }
//         }
//         @keyframes ringExpand {
//           0%   { transform: scale(0.45); opacity: 0.8; }
//           100% { transform: scale(1.7);  opacity: 0; }
//         }
//         @keyframes eqBar {
//           0%   { height: 5px; }
//           100% { height: 30px; }
//         }
//         @keyframes dotPulse {
//           0%, 100% { opacity: 1;   box-shadow: 0 0 10px currentColor; }
//           50%       { opacity: 0.4; box-shadow: 0 0 3px  currentColor; }
//         }
//         @keyframes ping {
//           0%   { transform: scale(1);   opacity: 0.9; }
//           80%  { transform: scale(2.4); opacity: 0; }
//           100% { transform: scale(2.8); opacity: 0; }
//         }
//         @keyframes popupIn {
//           from { opacity: 0; transform: translateY(18px) scale(0.93); }
//           to   { opacity: 1; transform: translateY(0)    scale(1); }
//         }
//         @keyframes fadeSlideIn {
//           from { opacity: 0; transform: translateY(8px); }
//           to   { opacity: 1; transform: translateY(0); }
//         }
//         @keyframes spin { to { transform: rotate(360deg); } }

//         .doit-log-scroll::-webkit-scrollbar { width: 3px; }
//         .doit-log-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }

//         .doit-main-btn {
//           transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease !important;
//         }
//         .doit-main-btn:hover:not(:disabled) {
//           transform: scale(1.07) !important;
//           filter: brightness(1.18) !important;
//         }
//         .doit-main-btn:active:not(:disabled) { transform: scale(0.95) !important; }
//         .doit-float-btn:hover { filter: brightness(1.1); }
//       `}</style>

//       {/* FLOATING ROBOT ICON */}
//       <button
//         className="doit-float-btn"
//         onClick={toggleOpen}
//         title="DOIT-AI · Agent905 Voice"
//         aria-label="Open DOIT AI Voice Assistant"
//         style={{
//           position:'fixed', bottom:'24px', right:'24px',
//           width:'84px', height:'84px',
//           borderRadius:'50%', border:'none',
//           background:'transparent', cursor:'pointer',
//           padding:0, zIndex:1001, outline:'none',
//           animation:'robotFloat 3.8s ease-in-out infinite',
//           transition:'filter 0.2s ease',
//         }}
//       >
//         <RobotSphere
//           expression={isOpen ? 'happy' : expression}
//           size={84}
//           glowColor={modeColor}
//           pulsing={mode === 'listening' || mode === 'speaking'}
//         />
//         {hasUnread && !isOpen && (
//           <span style={{
//             position:'absolute', top:'6px', right:'6px',
//             width:'13px', height:'13px',
//             background:'#f43f5e', borderRadius:'50%',
//             border:'2px solid #0c0f1a',
//             animation:'ping 1.3s ease infinite',
//           }} />
//         )}
//         {connected && (
//           <span style={{
//             position:'absolute', bottom:'8px', right:'8px',
//             width:'10px', height:'10px',
//             background:'#10b981', borderRadius:'50%',
//             border:'2px solid #0c0f1a',
//             boxShadow:'0 0 6px #10b981',
//           }} />
//         )}
//       </button>

//       {/* VOICE POPUP */}
//       {isOpen && (
//         <div style={{
//           position:'fixed',
//           bottom:'120px', right:'20px',
//           width:'340px',
//           maxWidth:'calc(100vw - 40px)',
//           borderRadius:'24px',
//           overflow:'hidden',
//           background:'linear-gradient(165deg, #08101f 0%, #0d1529 40%, #111e38 100%)',
//           border:'1px solid rgba(56,189,248,0.15)',
//           boxShadow:`
//             0 40px 90px rgba(0,0,0,0.75),
//             0 0 0 1px rgba(255,255,255,0.04),
//             inset 0 1px 0 rgba(255,255,255,0.06),
//             0 0 80px ${modeColor}0a
//           `,
//           zIndex:1000,
//           animation:'popupIn 0.3s cubic-bezier(0.34,1.4,0.64,1)',
//           fontFamily:"'Syne', sans-serif",
//           transition:'box-shadow 0.5s ease',
//         }}>

//           {/* Header */}
//           <div style={{
//             display:'flex', alignItems:'center', gap:'12px',
//             padding:'14px 16px 10px',
//             borderBottom:'1px solid rgba(255,255,255,0.045)',
//             background:'rgba(0,0,0,0.2)',
//           }}>
//             <RobotSphere expression={expression} size={38} glowColor={modeColor} />
//             <div style={{ flex:1 }}>
//               <div style={{ fontSize:'14px', fontWeight:800, color:'#f1f5f9', letterSpacing:'-0.02em' }}>
//                 DOIT-AI
//               </div>
//               <div style={{ fontSize:'9.5px', color:'#334155', fontFamily:"'JetBrains Mono', monospace", letterSpacing:'0.1em', marginTop:'1px' }}>
//                 AGENT905 · AZURE AI FOUNDRY · VOICE LIVE
//               </div>
//             </div>
//             {/* Live indicator */}
//             {connected && (
//               <div style={{
//                 display:'flex', alignItems:'center', gap:'5px',
//                 padding:'3px 8px', borderRadius:'100px',
//                 background:'rgba(16,185,129,0.12)', border:'1px solid rgba(16,185,129,0.3)',
//                 fontSize:'9px', fontFamily:"'JetBrains Mono', monospace",
//                 fontWeight:600, color:'#10b981', letterSpacing:'0.06em',
//               }}>
//                 <div style={{ width:'5px', height:'5px', borderRadius:'50%', background:'#10b981', animation:'dotPulse 1s ease infinite' }} />
//                 LIVE
//               </div>
//             )}
//             <button
//               onClick={toggleOpen}
//               style={{
//                 background:'rgba(255,255,255,0.04)', border:'1px solid rgba(255,255,255,0.07)',
//                 borderRadius:'9px', width:'30px', height:'30px',
//                 display:'flex', alignItems:'center', justifyContent:'center',
//                 cursor:'pointer', color:'#475569', fontSize:'15px',
//                 transition:'all 0.15s', outline:'none',
//               }}
//               onMouseEnter={e => { e.currentTarget.style.background='rgba(255,255,255,0.09)'; e.currentTarget.style.color='#94a3b8'; }}
//               onMouseLeave={e => { e.currentTarget.style.background='rgba(255,255,255,0.04)'; e.currentTarget.style.color='#475569'; }}
//             >✕</button>
//           </div>

//           {/* Body */}
//           <div style={{ padding:'22px 18px 16px', display:'flex', flexDirection:'column', alignItems:'center', gap:'16px' }}>

//             {/* Large Robot with rings */}
//             <div style={{ position:'relative', width:'158px', height:'158px', display:'flex', alignItems:'center', justifyContent:'center' }}>
//               <VoiceRings active={mode === 'listening'} color="#f43f5e" />
//               <VoiceRings active={mode === 'speaking'}  color="#10b981" />
//               <RobotSphere
//                 expression={expression}
//                 size={148}
//                 glowColor={modeColor}
//                 pulsing={mode === 'listening' || mode === 'processing' || mode === 'speaking' || mode === 'connecting'}
//               />
//               {(mode === 'connecting' || mode === 'processing') && (
//                 <div style={{
//                   position:'absolute', inset:'4px', borderRadius:'50%',
//                   border:'2px solid transparent',
//                   borderTopColor:'#f59e0b',
//                   borderRightColor:'#f59e0b33',
//                   animation:'spin 1.1s linear infinite',
//                   pointerEvents:'none',
//                 }} />
//               )}
//             </div>

//             {/* Status pill */}
//             <StatusPill label={statusLabel} color={modeColor} pulse={mode !== 'idle'} />

//             {/* Equalizer bars */}
//             <EqualizerBars active={mode === 'speaking'} color="#10b981" />

//             {/* Mic waveform (listening) */}
//             {mode === 'listening' && (
//               <div style={{ width:'100%', animation:'fadeSlideIn 0.2s ease' }}>
//                 <MicWave active />
//               </div>
//             )}

//             {/* Agent text while speaking */}
//             {mode === 'speaking' && botText && (
//               <div style={{
//                 width:'100%', padding:'10px 14px', borderRadius:'12px',
//                 background:'rgba(16,185,129,0.07)', border:'1px solid rgba(16,185,129,0.18)',
//                 color:'#6ee7b7', fontSize:'12.5px', lineHeight:'1.65',
//                 maxHeight:'82px', overflowY:'auto',
//                 animation:'fadeSlideIn 0.3s ease',
//               }}>
//                 {botText}
//               </div>
//             )}

//             {/* Connection info (idle, not connected) */}
//             {!connected && mode === 'idle' && (
//               <div style={{
//                 textAlign:'center', color:'#1e3a5f',
//                 fontSize:'11px', fontFamily:"'JetBrains Mono', monospace",
//                 lineHeight:'1.7',
//               }}>
//                 <div style={{ marginBottom:'4px' }}>Azure AI Foundry · Agent905</div>
//                 <div style={{ fontSize:'10px', color:'#152a45' }}>gpt-4o-realtime-preview · Steffan Dragon</div>
//               </div>
//             )}

//             {/* Error */}
//             {mode === 'error' && errorMsg && (
//               <div style={{
//                 width:'100%', padding:'8px 12px', borderRadius:'10px',
//                 background:'rgba(239,68,68,0.07)', border:'1px solid rgba(239,68,68,0.22)',
//                 color:'#fca5a5', fontSize:'12px',
//                 animation:'fadeSlideIn 0.2s ease',
//               }}>
//                 ⚠ {errorMsg}
//               </div>
//             )}

//             {/* Conversation log */}
//             {turns.length > 0 && mode !== 'speaking' && (
//               <div className="doit-log-scroll" style={{ width:'100%', animation:'fadeSlideIn 0.3s ease' }}>
//                 <div style={{
//                   fontSize:'9px', fontFamily:"'JetBrains Mono', monospace",
//                   color:'#1e3a5f', letterSpacing:'0.1em', textTransform:'uppercase',
//                   marginBottom:'8px',
//                 }}>
//                   Conversation
//                 </div>
//                 <ConversationLog turns={turns} />
//               </div>
//             )}

//             {/* MAIN BUTTON */}
//             <button
//               className="doit-main-btn"
//               onClick={handleMainButton}
//               disabled={mode === 'connecting' || mode === 'processing'}
//               aria-label={btnCfg.label}
//               style={{
//                 width:'76px', height:'76px', borderRadius:'50%',
//                 border:`2px solid ${btnCfg.border}`,
//                 background:btnCfg.bg, color:btnCfg.color,
//                 cursor:(mode === 'connecting' || mode === 'processing') ? 'not-allowed' : 'pointer',
//                 display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center',
//                 gap:'4px',
//                 boxShadow:`0 0 28px ${btnCfg.color}20, inset 0 1px 0 rgba(255,255,255,0.06)`,
//                 outline:'none',
//                 animation: mode === 'listening' ? 'dotPulse 1.2s ease infinite' : 'none',
//               }}
//             >
//               {btnCfg.icon}
//               <span style={{
//                 fontSize:'8.5px', fontFamily:"'JetBrains Mono', monospace",
//                 fontWeight:700, letterSpacing:'0.1em',
//               }}>
//                 {btnCfg.label}
//               </span>
//             </button>

//             {/* New conversation */}
//             {turns.length > 0 && (
//               <button
//                 onClick={() => { setTurns([]); setErrorMsg(''); agentTextBuf.current=''; userTextBuf.current=''; }}
//                 style={{
//                   background:'none', border:'none',
//                   color:'#1e3a5f', fontSize:'10.5px',
//                   fontFamily:"'JetBrains Mono', monospace",
//                   cursor:'pointer', letterSpacing:'0.04em',
//                   padding:'3px 8px', borderRadius:'6px',
//                   transition:'color 0.15s', outline:'none',
//                 }}
//                 onMouseEnter={e => e.currentTarget.style.color='#475569'}
//                 onMouseLeave={e => e.currentTarget.style.color='#1e3a5f'}
//               >
//                 ↺ New conversation
//               </button>
//             )}
//           </div>

//           {/* Footer */}
//           <div style={{
//             padding:'7px 16px 10px',
//             borderTop:'1px solid rgba(255,255,255,0.035)',
//             textAlign:'center',
//             fontSize:'9px', fontFamily:"'JetBrains Mono', monospace",
//             color:'#0f2035', letterSpacing:'0.07em',
//           }}>
//             DOIT-AI · Azure AI Foundry Agent905 · VoiceLive · PCM16 24kHz
//           </div>
//         </div>
//       )}
//     </>
//   );
// };

// export default AIChatbot;

/**
 * AIChatbot.js
 * DOIT-BOT — Voice Interface
 *
 * Pipeline: MediaRecorder → Azure Whisper STT → Azure AI Foundry Agent → Azure TTS
 *
 * No changes to the robot UI.  The only behavioural change is the backend
 * pipeline: instead of GPT-4o-mini chat-completions, the agent reply now
 * comes from the Azure AI Foundry Agent (asst_oZ98puGJjYE59Os9jz3NXbjU).
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import { voiceChatAPI } from '../../services/api';

/* ─── LED dot-matrix definitions ──────────────────────────────────────────── */
const GAP = 10, OX = 22, OY = 52, DOT = 4.2;

const EXPRESSIONS = {
  idle: {
    leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
    rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
    mouth:    [[4,3],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,3]],
  },
  listening: {
    leftEye:  [[2,0],[3,0],[4,0],[5,0],[6,0]],
    rightEye: [[10,0],[11,0],[12,0],[13,0],[14,0]],
    mouth:    [[6,3],[7,3],[8,3],[9,3],[10,3]],
  },
  thinking: {
    leftEye:  [[2,0],[3,1],[4,0],[5,1],[6,0]],
    rightEye: [[10,0],[11,1],[12,0],[13,1],[14,0]],
    mouth:    [[5,3],[6,3],[7,3],[9,3],[10,3],[11,3]],
  },
  speaking: {
    leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
    rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
    mouth:    [[4,3],[5,3],[6,3],[7,3],[8,3],[9,3],[10,3],[11,3],
               [4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4]],
  },
  happy: {
    leftEye:  [[2,1],[3,0],[4,0],[5,0],[6,1]],
    rightEye: [[10,1],[11,0],[12,0],[13,0],[14,1]],
    mouth:    [[3,3],[4,4],[5,4],[6,4],[7,4],[8,4],[9,4],[10,4],[11,4],[12,3]],
  },
  error: {
    leftEye:  [[2,0],[3,0],[4,1],[5,0],[6,0]],
    rightEye: [[10,0],[11,0],[12,1],[13,0],[14,0]],
    mouth:    [[4,4],[5,3],[6,3],[7,3],[8,3],[9,3],[10,3],[11,4]],
  },
};

/* ─── SVG components ──────────────────────────────────────────────────────── */
function LedFace({ expression = 'idle', glowColor = '#38bdf8' }) {
  const expr = EXPRESSIONS[expression] || EXPRESSIONS.idle;
  const dots = [...expr.leftEye, ...expr.rightEye, ...expr.mouth];
  return (
    <>
      {dots.map(([gx, gy], i) => (
        <circle
          key={i}
          cx={OX + gx * GAP}
          cy={OY + gy * GAP}
          r={DOT}
          fill={glowColor}
          style={{
            filter: `drop-shadow(0 0 5px ${glowColor}) drop-shadow(0 0 10px ${glowColor}88)`,
            transition: 'all 0.12s ease',
          }}
        />
      ))}
    </>
  );
}

function RobotSphere({ expression, size = 80, glowColor = '#38bdf8', pulsing = false }) {
  const uid = `rs_${size}`;
  return (
    <svg
      width={size} height={size}
      viewBox="0 0 180 200"
      xmlns="http://www.w3.org/2000/svg"
      style={{
        display: 'block',
        filter: pulsing
          ? `drop-shadow(0 0 18px ${glowColor}) drop-shadow(0 8px 24px ${glowColor}66)`
          : `drop-shadow(0 8px 24px ${glowColor}44) drop-shadow(0 2px 8px rgba(0,0,0,0.5))`,
        transition: 'filter 0.35s ease',
      }}
    >
      <defs>
        <linearGradient id={`chrome_${uid}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"   stopColor="#9ca3af" />
          <stop offset="30%"  stopColor="#e5e7eb" />
          <stop offset="60%"  stopColor="#6b7280" />
          <stop offset="100%" stopColor="#374151" />
        </linearGradient>
        <radialGradient id={`sphere_${uid}`} cx="38%" cy="30%" r="65%">
          <stop offset="0%"   stopColor="#1e293b" stopOpacity="0.7" />
          <stop offset="60%"  stopColor="#0f172a" stopOpacity="0.92" />
          <stop offset="100%" stopColor="#020617" />
        </radialGradient>
        <radialGradient id={`sheen_${uid}`} cx="30%" cy="22%" r="50%">
          <stop offset="0%"   stopColor="white"  stopOpacity="0.3" />
          <stop offset="100%" stopColor="white"  stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`glow_${uid}`} cx="50%" cy="90%" r="50%">
          <stop offset="0%"   stopColor={glowColor} stopOpacity="0.2" />
          <stop offset="100%" stopColor={glowColor} stopOpacity="0" />
        </radialGradient>
        <radialGradient id={`cap_${uid}`} cx="35%" cy="30%" r="65%">
          <stop offset="0%"   stopColor={glowColor} />
          <stop offset="100%" stopColor={glowColor} stopOpacity="0.4" />
        </radialGradient>
        <linearGradient id={`ear_${uid}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%"   stopColor="#374151" />
          <stop offset="100%" stopColor="#111827" />
        </linearGradient>
      </defs>

      {/* Antenna */}
      <line x1="108" y1="8" x2="120" y2="30" stroke="#9ca3af" strokeWidth="2.5" strokeLinecap="round"/>
      <circle cx="120" cy="28" r="5" fill={`url(#cap_${uid})`}
        style={{ filter: `drop-shadow(0 0 6px ${glowColor})` }} />

      {/* Chrome ring */}
      <circle cx="90" cy="98" r="76" fill={`url(#chrome_${uid})`} />

      {/* Dark face plate */}
      <circle cx="90" cy="98" r="68" fill={`url(#sphere_${uid})`} />

      {/* LED face */}
      <LedFace expression={expression} glowColor={glowColor} />

      {/* Glass sheen */}
      <ellipse cx="72" cy="72" rx="46" ry="36" fill={`url(#sheen_${uid})`} />

      {/* Bottom glow */}
      <circle cx="90" cy="98" r="68" fill={`url(#glow_${uid})`} />

      {/* Ears */}
      <ellipse cx="16"  cy="98" rx="10" ry="14" fill={`url(#ear_${uid})`} stroke="#4b5563" strokeWidth="1"/>
      <ellipse cx="16"  cy="98" rx="5"  ry="8"  fill={glowColor} opacity="0.25" />
      <ellipse cx="164" cy="98" rx="10" ry="14" fill={`url(#ear_${uid})`} stroke="#4b5563" strokeWidth="1"/>
      <ellipse cx="164" cy="98" rx="5"  ry="8"  fill={glowColor} opacity="0.25" />

      {/* Bow tie */}
      <polygon points="74,170 88,163 88,177" fill="#1e293b" stroke="#374151" strokeWidth="1"/>
      <polygon points="106,170 92,163 92,177" fill="#1e293b" stroke="#374151" strokeWidth="1"/>
      <ellipse cx="90" cy="170" rx="6" ry="5" fill="#374151" stroke="#4b5563" strokeWidth="1"/>
    </svg>
  );
}

function VoiceRings({ active, color }) {
  if (!active) return null;
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          position: 'absolute',
          width: `${90 + i * 38}px`, height: `${90 + i * 38}px`,
          borderRadius: '50%',
          border: `1.5px solid ${color}`,
          opacity: 0,
          animation: `ringExpand 2.2s ease-out ${i * 0.55}s infinite`,
        }} />
      ))}
    </div>
  );
}

function EqualizerBars({ active, color }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      gap: '3px', height: '36px',
      opacity: active ? 1 : 0.12,
      transition: 'opacity 0.4s ease',
    }}>
      {Array.from({ length: 20 }).map((_, i) => (
        <div key={i} style={{
          width: '3px', borderRadius: '2px',
          background: color,
          boxShadow: active ? `0 0 6px ${color}88` : 'none',
          height: '6px',
          animation: active ? `eqBar 0.${4 + (i % 5)}s ease-in-out ${i * 0.04}s infinite alternate` : 'none',
        }} />
      ))}
    </div>
  );
}

function MicWave({ active }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', height: '30px' }}>
      {Array.from({ length: 14 }).map((_, i) => (
        <div key={i} style={{
          width: '3px', borderRadius: '2px',
          background: '#f43f5e',
          boxShadow: active ? '0 0 6px #f43f5e88' : 'none',
          height: active ? `${6 + (i % 5) * 5}px` : '5px',
          animation: active ? `eqBar 0.${3 + (i % 4)}s ease-in-out ${i * 0.05}s infinite alternate` : 'none',
          opacity: active ? 1 : 0.18,
          transition: 'all 0.2s',
        }} />
      ))}
    </div>
  );
}

function StatusPill({ label, color, pulse }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: '7px',
      padding: '5px 16px', borderRadius: '100px',
      background: `${color}12`, border: `1px solid ${color}35`,
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: '11px', fontWeight: 600, color, letterSpacing: '0.07em',
    }}>
      <div style={{
        width: '7px', height: '7px', borderRadius: '50%',
        background: color, boxShadow: `0 0 8px ${color}`,
        animation: pulse ? 'dotPulse 1s ease-in-out infinite' : 'none',
      }} />
      {label}
    </div>
  );
}

function TranscriptBubble({ text, role }) {
  if (!text) return null;
  const isUser = role === 'user';
  return (
    <div style={{
      padding: '9px 13px',
      borderRadius: isUser ? '14px 14px 3px 14px' : '3px 14px 14px 14px',
      background: isUser ? 'rgba(244,63,94,0.1)' : 'rgba(56,189,248,0.07)',
      border: `1px solid ${isUser ? 'rgba(244,63,94,0.22)' : 'rgba(56,189,248,0.18)'}`,
      color: isUser ? '#fda4af' : '#bae6fd',
      fontSize: '12.5px', lineHeight: '1.6',
      fontFamily: "'Syne', sans-serif",
      wordBreak: 'break-word',
      animation: 'fadeSlideIn 0.25s ease',
    }}>
      <span style={{ fontSize: '9px', opacity: 0.5, display: 'block', marginBottom: '3px', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.06em' }}>
        {isUser ? '👤 YOU' : '🤖 DOIT-AI'}
      </span>
      {text}
    </div>
  );
}

function ConversationLog({ turns }) {
  const logRef = useRef(null);
  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: 'smooth' });
  }, [turns]);
  if (!turns.length) return null;
  return (
    <div ref={logRef} style={{
      width: '100%', maxHeight: '150px', overflowY: 'auto',
      display: 'flex', flexDirection: 'column', gap: '8px',
      padding: '0 1px',
      scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.08) transparent',
    }}>
      {turns.slice(-5).map((t, i) => (
        <TranscriptBubble key={i} text={t.text} role={t.role} />
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ═══════════════════════════════════════════════════════════════════════════ */
const AIChatbot = ({ user }) => {
  const [isOpen,      setIsOpen]      = useState(false);
  const [mode,        setMode]        = useState('idle');
  // mode: 'idle' | 'listening' | 'processing' | 'speaking' | 'error'
  const [expression,  setExpression]  = useState('idle');
  const [statusLabel, setStatusLabel] = useState('Tap mic to speak');
  const [botText,     setBotText]     = useState('');
  const [turns,       setTurns]       = useState([]);
  const [errorMsg,    setErrorMsg]    = useState('');
  const [hasUnread,   setHasUnread]   = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef   = useRef([]);
  const exprTimer        = useRef(null);
  const audioRef         = useRef(null);

  /* ── Color per mode ────────────────────────────────────────────── */
  const modeColor = {
    idle:       '#38bdf8',
    listening:  '#f43f5e',
    processing: '#f59e0b',
    speaking:   '#10b981',
    error:      '#ef4444',
  }[mode] || '#38bdf8';

  /* ── Expression helper ────────────────────────────────────────── */
  const setExpr = useCallback((expr, ttl) => {
    clearTimeout(exprTimer.current);
    setExpression(expr);
    if (ttl) exprTimer.current = setTimeout(() => setExpression('idle'), ttl);
  }, []);

  /* ── Start recording ─────────────────────────────────────────── */
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const mimeType = MediaRecorder.isTypeSupported('audio/webm')
        ? 'audio/webm'
        : 'audio/mp4';

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current   = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        stream.getTracks().forEach(t => t.stop());
        await sendAudioToBackend(audioBlob);
      };

      mediaRecorder.start();
      setMode('listening');
      setExpr('listening');
      setStatusLabel('Listening… speak now');
    } catch (err) {
      console.error('Microphone error:', err);
      setErrorMsg('Microphone access denied');
      setMode('error');
      setExpr('error', 3000);
      setTimeout(() => { setMode('idle'); setStatusLabel('Tap mic to speak'); }, 3500);
    }
  }, [setExpr]);

  /* ── Stop recording ──────────────────────────────────────────── */
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  /* ── Send audio → backend (Whisper → Foundry Agent → TTS) ───── */
  const sendAudioToBackend = async (audioBlob) => {
    setMode('processing');
    setExpr('thinking');
    setStatusLabel('Thinking…');

    try {
      // Build conversation history for the agent
      const history = turns.map(t => ({
        role:    t.role === 'user' ? 'user' : 'assistant',
        content: t.text,
      }));

      // voiceChatAPI.chat → POST /api/voice-chat/voice/chat
      // Backend: Whisper → Foundry Agent → TTS
      const result = await voiceChatAPI.chat(audioBlob, 'friendly', history);

      const transcript   = result.transcript   || 'Voice input';
      const responseText = result.responseText || '';

      // Add both turns to conversation log
      setTurns(prev => [
        ...prev,
        { role: 'user', text: transcript },
        { role: 'bot',  text: responseText },
      ]);

      // Play TTS audio
      setMode('speaking');
      setExpr('speaking');
      setStatusLabel('Speaking…');
      setBotText(responseText);

      const audioUrl = URL.createObjectURL(result.audioBlob);
      const audio    = new Audio(audioUrl);
      audioRef.current = audio;

      audio.onended = () => {
        setMode('idle');
        setExpr('happy', 2500);
        setStatusLabel('Tap mic to speak');
        setBotText('');
        if (!isOpen) setHasUnread(true);
        URL.revokeObjectURL(audioUrl);
      };

      audio.onerror = () => {
        setMode('error');
        setExpr('error', 3000);
        setStatusLabel('Playback failed');
        setTimeout(() => { setMode('idle'); setStatusLabel('Tap mic to speak'); }, 3500);
        URL.revokeObjectURL(audioUrl);
      };

      audio.play();

    } catch (err) {
      console.error('Voice chat error:', err);
      setErrorMsg(err.message || 'Voice chat failed');
      setMode('error');
      setExpr('error', 3500);
      setStatusLabel('Error — tap to retry');
      setTimeout(() => {
        setMode('idle');
        setStatusLabel('Tap mic to speak');
        setErrorMsg('');
      }, 4500);
    }
  };

  /* ── Stop all ────────────────────────────────────────────────── */
  const stopAll = useCallback(() => {
    try { mediaRecorderRef.current?.stop(); } catch (_) {}
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; }
    clearTimeout(exprTimer.current);
    setMode('idle');
    setExpression('idle');
    setStatusLabel('Tap mic to speak');
    setBotText('');
  }, []);

  /* ── Toggle popup ────────────────────────────────────────────── */
  const toggleOpen = useCallback(() => {
    setIsOpen(prev => {
      const next = !prev;
      if (next) {
        setHasUnread(false);
        setExpr('happy', 1800);
        setStatusLabel('Tap mic to speak');
      } else {
        stopAll();
      }
      return next;
    });
  }, [stopAll, setExpr]);

  /* ── Mic button handler ──────────────────────────────────────── */
  const handleMicPress = () => {
    if (mode === 'listening')  { stopRecording(); return; }
    if (mode === 'speaking')   { stopAll();       return; }
    if (mode === 'processing') return;
    startRecording();
  };

  /* ── Cleanup ─────────────────────────────────────────────────── */
  useEffect(() => () => stopAll(), [stopAll]);

  /* ── Mic button config per mode ─────────────────────────────── */
  const MicIconSVG = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="23"/>
      <line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
  );
  const StopIconSVG = () => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="3"/>
    </svg>
  );
  const SpinnerSVG = () => (
    <div style={{ width: '22px', height: '22px', border: '2px solid transparent', borderTopColor: '#f59e0b', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
  );

  const micCfg = {
    idle:       { icon: <MicIconSVG  />, label: 'SPEAK', color: '#38bdf8', bg: 'rgba(56,189,248,0.1)',  border: 'rgba(56,189,248,0.3)'  },
    listening:  { icon: <StopIconSVG />, label: 'STOP',  color: '#f43f5e', bg: 'rgba(244,63,94,0.12)', border: 'rgba(244,63,94,0.35)'  },
    processing: { icon: <SpinnerSVG  />, label: 'WAIT',  color: '#f59e0b', bg: 'rgba(245,158,11,0.08)',border: 'rgba(245,158,11,0.25)' },
    speaking:   { icon: <StopIconSVG />, label: 'STOP',  color: '#10b981', bg: 'rgba(16,185,129,0.1)', border: 'rgba(16,185,129,0.3)'  },
    error:      { icon: <MicIconSVG  />, label: 'RETRY', color: '#ef4444', bg: 'rgba(239,68,68,0.1)',  border: 'rgba(239,68,68,0.3)'   },
  }[mode];

  /* ─────────────────────────────────────────────────────────────
     RENDER
  ────────────────────────────────────────────────────────────── */
  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

        @keyframes robotFloat {
          0%, 100% { transform: translateY(0px); }
          50%       { transform: translateY(-7px); }
        }
        @keyframes ringExpand {
          0%   { transform: scale(0.45); opacity: 0.8; }
          100% { transform: scale(1.7);  opacity: 0; }
        }
        @keyframes eqBar {
          0%   { height: 5px; }
          100% { height: 30px; }
        }
        @keyframes dotPulse {
          0%, 100% { opacity: 1;   box-shadow: 0 0 10px currentColor; }
          50%       { opacity: 0.4; box-shadow: 0 0 3px  currentColor; }
        }
        @keyframes ping {
          0%   { transform: scale(1);   opacity: 0.9; }
          80%  { transform: scale(2.4); opacity: 0; }
          100% { transform: scale(2.8); opacity: 0; }
        }
        @keyframes popupIn {
          from { opacity: 0; transform: translateY(18px) scale(0.93); }
          to   { opacity: 1; transform: translateY(0)    scale(1); }
        }
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        .doit-log-scroll::-webkit-scrollbar { width: 3px; }
        .doit-log-scroll::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.08); border-radius: 3px; }
        .doit-mic-btn { transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease !important; }
        .doit-mic-btn:hover:not(:disabled) { transform: scale(1.07) !important; filter: brightness(1.18) !important; }
        .doit-mic-btn:active:not(:disabled) { transform: scale(0.95) !important; }
        .doit-float-btn:hover { filter: brightness(1.1); }
      `}</style>

      {/* ── Floating robot icon ── */}
      <button
        className="doit-float-btn"
        onClick={toggleOpen}
        title="DOIT-AI Voice Assistant"
        aria-label="Open DOIT AI Voice Assistant"
        style={{
          position: 'fixed', bottom: '24px', right: '24px',
          width: '84px', height: '84px',
          borderRadius: '50%', border: 'none',
          background: 'transparent', cursor: 'pointer',
          padding: 0, zIndex: 1001, outline: 'none',
          animation: 'robotFloat 3.8s ease-in-out infinite',
          transition: 'filter 0.2s ease',
        }}
      >
        <RobotSphere
          expression={isOpen ? 'happy' : expression}
          size={84}
          glowColor={modeColor}
          pulsing={mode === 'listening' || mode === 'speaking'}
        />
        {hasUnread && !isOpen && (
          <span style={{
            position: 'absolute', top: '6px', right: '6px',
            width: '13px', height: '13px',
            background: '#f43f5e', borderRadius: '50%',
            border: '2px solid #0c0f1a',
            animation: 'ping 1.3s ease infinite',
          }} />
        )}
      </button>

      {/* ── Voice popup ── */}
      {isOpen && (
        <div style={{
          position: 'fixed',
          bottom: '120px', right: '20px',
          width: '340px',
          maxWidth: 'calc(100vw - 40px)',
          borderRadius: '24px',
          overflow: 'hidden',
          background: 'linear-gradient(165deg, #08101f 0%, #0d1529 40%, #111e38 100%)',
          border: '1px solid rgba(56,189,248,0.15)',
          boxShadow: `
            0 40px 90px rgba(0,0,0,0.75),
            0 0 0 1px rgba(255,255,255,0.04),
            inset 0 1px 0 rgba(255,255,255,0.06),
            0 0 80px ${modeColor}0a
          `,
          zIndex: 1000,
          animation: 'popupIn 0.3s cubic-bezier(0.34,1.4,0.64,1)',
          fontFamily: "'Syne', sans-serif",
          transition: 'box-shadow 0.5s ease',
        }}>

          {/* Header */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: '12px',
            padding: '14px 16px 10px',
            borderBottom: '1px solid rgba(255,255,255,0.045)',
            background: 'rgba(0,0,0,0.2)',
          }}>
            <RobotSphere expression={expression} size={38} glowColor={modeColor} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '14px', fontWeight: 800, color: '#f1f5f9', letterSpacing: '-0.02em' }}>
                DOIT-AI
              </div>
              {/* ← Updated label to reflect Foundry Agent pipeline */}
              <div style={{ fontSize: '9.5px', color: '#334155', fontFamily: "'JetBrains Mono', monospace", letterSpacing: '0.1em', marginTop: '1px' }}>
                WHISPER · FOUNDRY AGENT · TTS
              </div>
            </div>
            <button
              onClick={toggleOpen}
              style={{
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)',
                borderRadius: '9px', width: '30px', height: '30px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', color: '#475569', fontSize: '15px',
                transition: 'all 0.15s', outline: 'none',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.09)'; e.currentTarget.style.color = '#94a3b8'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = '#475569'; }}
            >✕</button>
          </div>

          {/* Body */}
          <div style={{ padding: '22px 18px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>

            {/* Large robot with rings */}
            <div style={{ position: 'relative', width: '158px', height: '158px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <VoiceRings active={mode === 'listening'} color="#f43f5e" />
              <VoiceRings active={mode === 'speaking'}  color="#10b981" />
              <RobotSphere
                expression={expression}
                size={148}
                glowColor={modeColor}
                pulsing={mode === 'listening' || mode === 'processing' || mode === 'speaking'}
              />
              {mode === 'processing' && (
                <div style={{
                  position: 'absolute', inset: '4px', borderRadius: '50%',
                  border: '2px solid transparent',
                  borderTopColor: '#f59e0b',
                  borderRightColor: '#f59e0b33',
                  animation: 'spin 1.1s linear infinite',
                  pointerEvents: 'none',
                }} />
              )}
            </div>

            <StatusPill label={statusLabel} color={modeColor} pulse={mode !== 'idle'} />

            <EqualizerBars active={mode === 'speaking'} color="#10b981" />

            {mode === 'listening' && (
              <div style={{ width: '100%', animation: 'fadeSlideIn 0.2s ease' }}>
                <MicWave active />
              </div>
            )}

            {mode === 'speaking' && botText && (
              <div style={{
                width: '100%', padding: '10px 14px', borderRadius: '12px',
                background: 'rgba(16,185,129,0.07)', border: '1px solid rgba(16,185,129,0.18)',
                color: '#6ee7b7', fontSize: '12.5px', lineHeight: '1.65',
                maxHeight: '82px', overflowY: 'auto',
                animation: 'fadeSlideIn 0.3s ease',
              }}>
                {botText}
              </div>
            )}

            {mode === 'error' && errorMsg && (
              <div style={{
                width: '100%', padding: '8px 12px', borderRadius: '10px',
                background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.22)',
                color: '#fca5a5', fontSize: '12px',
                animation: 'fadeSlideIn 0.2s ease',
              }}>
                ⚠ {errorMsg}
              </div>
            )}

            {turns.length > 0 && mode === 'idle' && (
              <div className="doit-log-scroll" style={{ width: '100%', animation: 'fadeSlideIn 0.3s ease' }}>
                <div style={{
                  fontSize: '9px', fontFamily: "'JetBrains Mono', monospace",
                  color: '#1e3a5f', letterSpacing: '0.1em', textTransform: 'uppercase',
                  marginBottom: '8px',
                }}>
                  Conversation
                </div>
                <ConversationLog turns={turns} />
              </div>
            )}

            {/* Mic button */}
            <button
              className="doit-mic-btn"
              onClick={handleMicPress}
              disabled={mode === 'processing'}
              aria-label={micCfg.label}
              style={{
                width: '76px', height: '76px', borderRadius: '50%',
                border: `2px solid ${micCfg.border}`,
                background: micCfg.bg, color: micCfg.color,
                cursor: mode === 'processing' ? 'not-allowed' : 'pointer',
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                gap: '4px',
                boxShadow: `0 0 28px ${micCfg.color}20, inset 0 1px 0 rgba(255,255,255,0.06)`,
                outline: 'none',
                animation: mode === 'listening' ? 'dotPulse 1.2s ease infinite' : 'none',
              }}
            >
              {micCfg.icon}
              <span style={{ fontSize: '8.5px', fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, letterSpacing: '0.1em' }}>
                {micCfg.label}
              </span>
            </button>

            {turns.length > 0 && (
              <button
                onClick={() => { stopAll(); setTurns([]); setErrorMsg(''); }}
                style={{
                  background: 'none', border: 'none',
                  color: '#1e3a5f', fontSize: '10.5px',
                  fontFamily: "'JetBrains Mono', monospace",
                  cursor: 'pointer', letterSpacing: '0.04em',
                  padding: '3px 8px', borderRadius: '6px',
                  transition: 'color 0.15s', outline: 'none',
                }}
                onMouseEnter={e => e.currentTarget.style.color = '#475569'}
                onMouseLeave={e => e.currentTarget.style.color = '#1e3a5f'}
              >
                ↺ New conversation
              </button>
            )}
          </div>

          {/* Footer */}
          <div style={{
            padding: '7px 16px 10px',
            borderTop: '1px solid rgba(255,255,255,0.035)',
            textAlign: 'center',
            fontSize: '9px', fontFamily: "'JetBrains Mono', monospace",
            color: '#0f2035', letterSpacing: '0.07em',
          }}>
            DOIT-AI · Whisper STT · Foundry Agent · Azure TTS
          </div>
        </div>
      )}
    </>
  );
};

export default AIChatbot;