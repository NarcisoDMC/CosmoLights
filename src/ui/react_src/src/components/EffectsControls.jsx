import React, { useState } from 'react';
import {
  Sparkles,
  Zap,
  Flame,
  Wind,
  Volume2,
  Music,
  Radio,
  Sliders,
  Gauge,
  Activity,
  Heart,
  Orbit,
  Star,
  Siren,
  Waves,
} from 'lucide-react';

const EFFECTS = [
  {
    id: 'rainbow_flow',
    name: 'Gradiente en Giro',
    category: 'visual',
    desc: 'Rotación cromática suave y continua a lo largo de las 3 tiras.',
    icon: Sparkles,
    badge: 'Cromático',
    color: 'text-amber-400',
  },
  {
    id: 'meteor_chaser',
    name: 'Barra Móvil Cromática',
    category: 'visual',
    desc: 'Barra de luz pequeña que viaja por la tira, muta de color y deja estela.',
    icon: Flame,
    badge: 'Dinámico',
    color: 'text-cyan-400',
  },
  {
    id: 'cosmic_aurora',
    name: 'Aurora Cósmica',
    category: 'visual',
    desc: 'Ondas bioluminiscentes de cian, verde esmeralda y violeta profundo.',
    icon: Wind,
    badge: 'Ambiente',
    color: 'text-purple-400',
  },
  {
    id: 'fire_ember',
    name: 'Fuego & Brasas',
    category: 'visual',
    desc: 'Llamas ardientes con propagación térmica realista y chispas incandescentes.',
    icon: Flame,
    badge: 'Térmico',
    color: 'text-orange-500',
  },
  {
    id: 'cyberpunk_breath',
    name: 'Respiración Neón',
    category: 'visual',
    desc: 'Inhalación y exhalación orgánica de luz entre tonos magenta y violeta.',
    icon: Heart,
    badge: 'Relax / Chill',
    color: 'text-pink-400',
  },
  {
    id: 'plasma_waves',
    name: 'Plasma Cósmico',
    category: 'visual',
    desc: 'Campos de energía oscilantes de alta fluidez electromagnética.',
    icon: Orbit,
    badge: 'Fluido',
    color: 'text-indigo-400',
  },
  {
    id: 'starlight_twinkle',
    name: 'Cielo Estrellado',
    category: 'visual',
    desc: 'Destellos aleatorios de estrellas brillantes sobre fondo azul noche.',
    icon: Star,
    badge: 'Espacial',
    color: 'text-yellow-300',
  },
  {
    id: 'police_strobe',
    name: 'Estroboscópico Patrulla',
    category: 'visual',
    desc: 'Destellos de emergencia policiales alternados de alta cadencia.',
    icon: Siren,
    badge: 'Strobe',
    color: 'text-red-500',
  },
  {
    id: 'audio_converge',
    name: 'Espectro Convergente',
    category: 'audio',
    desc: 'La luz sube por ambos lados al ritmo del sonido y colisiona arriba cambiando de color.',
    icon: Music,
    badge: 'Audio Reactivo',
    color: 'text-emerald-400',
  },
  {
    id: 'audio_pulse',
    name: 'Pulso de Graves',
    category: 'audio',
    desc: 'Respiración de volumen con destellos y cambio de color en los golpes de bajo.',
    icon: Volume2,
    badge: 'Beat / Bajos',
    color: 'text-rose-400',
  },
  {
    id: 'audio_eq',
    name: 'Ecualizador 3 Bandas',
    category: 'audio',
    desc: 'Graves en los laterales, medios en esquinas superiores y agudos al centro.',
    icon: Radio,
    badge: 'Frecuencias',
    color: 'text-blue-400',
  },
  {
    id: 'audio_ripple',
    name: 'Onda Expansiva',
    category: 'audio',
    desc: 'Propagación radial expansiva desde la parte superior al detectar beats.',
    icon: Waves,
    badge: 'Shockwave',
    color: 'text-teal-400',
  },
];

export default function EffectsControls({
  activeEffect,
  onSetEffect,
  speed,
  onSetSpeed,
  sensitivity,
  onSetSensitivity,
}) {
  const [filter, setFilter] = useState('all');

  const filteredEffects = EFFECTS.filter((e) => {
    if (filter === 'all') return true;
    return e.category === filter;
  });

  const isAudioActive = activeEffect && activeEffect.startsWith('audio');

  return (
    <div className="flex flex-col gap-5">
      {/* Header and Filter Category Tabs */}
      <div className="bg-[#10131e]/90 border border-[#22273d] rounded-2xl p-5 flex flex-col gap-4 backdrop-blur-md shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <div className="text-base font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-purple-400" />
              Efectos Algorítmicos & Audio Visualizer
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Patrones procedurales generados por software a 40 FPS y reactivos a la música.
            </p>
          </div>

          {/* Categorías */}
          <div className="flex items-center gap-1.5 bg-[#161a29] p-1 rounded-xl border border-[#22273d]">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                filter === 'all'
                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Todos ({EFFECTS.length})
            </button>
            <button
              onClick={() => setFilter('visual')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                filter === 'visual'
                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Visuales
            </button>
            <button
              onClick={() => setFilter('audio')}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer ${
                filter === 'audio'
                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              Audio Reactivo
            </button>
          </div>
        </div>

        {/* Global Controls: Speed & Audio Sensitivity */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 border-t border-[#22273d]/70">
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-300 flex items-center gap-1.5">
                <Gauge className="w-3.5 h-3.5 text-purple-400" />
                Velocidad del Efecto
              </span>
              <span className="text-purple-400 font-bold">{speed.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="0.2"
              max="3.0"
              step="0.1"
              value={speed}
              onChange={(e) => onSetSpeed(parseFloat(e.target.value))}
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>0.2x (Lento)</span>
              <span>1.0x (Normal)</span>
              <span>3.0x (Rápido)</span>
            </div>
          </div>

          <div
            className={`flex flex-col gap-2 transition-opacity ${
              isAudioActive ? 'opacity-100' : 'opacity-40 pointer-events-none'
            }`}
          >
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-300 flex items-center gap-1.5">
                <Sliders className="w-3.5 h-3.5 text-emerald-400" />
                Sensibilidad WASAPI Loopback
              </span>
              <span className="text-emerald-400 font-bold">{sensitivity.toFixed(1)}x</span>
            </div>
            <input
              type="range"
              min="0.5"
              max="2.5"
              step="0.1"
              value={sensitivity}
              onChange={(e) => onSetSensitivity(parseFloat(e.target.value))}
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>Suave</span>
              <span>Muy Reactivo</span>
            </div>
          </div>
        </div>
      </div>

      {/* Effects Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredEffects.map((eff) => {
          const IconComp = eff.icon;
          const isActive = activeEffect === eff.id;

          return (
            <button
              key={eff.id}
              onClick={() => onSetEffect(eff.id)}
              className={`text-left p-4 rounded-xl flex items-start gap-3.5 transition-all duration-200 cursor-pointer shadow-md active:scale-[0.98] ${
                isActive
                  ? 'bg-gradient-to-r from-[#18233d] to-[#1e1c3a] border-2 border-purple-400 shadow-purple-500/25'
                  : 'bg-[#10131e]/90 hover:bg-[#161a29] border border-[#22273d] hover:border-slate-600'
              }`}
            >
              <div
                className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border transition-transform ${
                  isActive
                    ? 'bg-purple-500/20 border-purple-400 shadow-[0_0_12px_rgba(192,132,252,0.4)] scale-105'
                    : 'bg-[#161a29] border-[#22273d]'
                }`}
              >
                <IconComp className={`w-5 h-5 ${eff.color}`} />
              </div>

              <div className="flex-1">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-bold text-white flex items-center gap-2">
                    {eff.name}
                    {isActive && (
                      <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping" />
                    )}
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                      eff.category === 'audio'
                        ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                        : 'bg-purple-500/15 text-purple-400 border border-purple-500/30'
                    }`}
                  >
                    {eff.badge}
                  </span>
                </div>
                <div className="text-xs text-slate-400 font-normal mt-1 leading-relaxed">
                  {eff.desc}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
