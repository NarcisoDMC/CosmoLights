import React from 'react';
import { Play, Square, Compass, Sliders, Layers, Info, Film, Sparkles, RefreshCw } from 'lucide-react';

export default function AmbilightControls({
  isRunning,
  onToggle,
  config,
  onUpdateConfig,
  monitors,
  selectedMonitor,
  onSelectMonitor,
  onRefreshMonitors,
  detectedAspect = '16:9',
  cropTopPct = 0,
}) {
  const {
    start_side = 'left',
    reverse_order = false,
    zone_offset = 0,
    smoothing = 0.4,
    saturation_boost = 1.25,
    target_fps = 30,
    aspect_ratio = 'auto',
    black_cutoff = 15,
    gamma = 2.0,
  } = config;

  const handleStartSideChange = (e) => {
    onUpdateConfig({ start_side: e.target.value });
  };

  const handleReverseChange = (e) => {
    onUpdateConfig({ reverse_order: e.target.value === 'true' });
  };

  const handleOffsetChange = (delta) => {
    const nextOffset = Math.max(-33, Math.min(33, (zone_offset || 0) + delta));
    onUpdateConfig({ zone_offset: nextOffset });
  };

  const handleAspectRatioChange = (newRatio) => {
    onUpdateConfig({ aspect_ratio: newRatio });
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Master Toggle Card */}
      <div className="bg-[#10131e]/90 border border-[#22273d] rounded-2xl p-5 flex items-center justify-between backdrop-blur-md shadow-lg">
        <div>
          <div className="text-base font-bold text-white flex items-center gap-2">
            <Layers className="w-5 h-5 text-purple-400" />
            Captura y Sincronización en Vivo
          </div>
          <p className="text-xs text-slate-400 mt-1 mr-2">
            Sincroniza los 63 LEDs físicos (17 Izq + 29 Arriba + 17 Der) en tiempo real con los bordes de la pantalla.
          </p>
        </div>

        <button
          onClick={onToggle}
          className={`px-6 py-2 rounded-3xl font-bold text-sm flex items-center gap-2.5 transition-all duration-200 cursor-pointer shadow-lg hover:scale-105 active:scale-95 ${
            isRunning
              ? 'bg-gradient-to-r from-red-500 to-rose-600 text-white shadow-red-500/30'
              : 'bg-gradient-to-r from-purple-400 to-indigo-500 text-slate-950 shadow-purple-400/30'
          }`}
        >
          {isRunning ? (
            <>
              <Square className="w-4 h-4 fill-current" />
              <span>Detener Ambilight</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Iniciar Ambilight</span>
            </>
          )}
        </button>
      </div>

      {/* Relación de Aspecto & Detección Inteligente de Barras Negras */}
      <div className="bg-[#10131e]/90 border border-[#22273d] rounded-2xl p-5 flex flex-col gap-4 backdrop-blur-md shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-[#22273d]/70 pb-3">
          <div>
            <div className="text-sm font-bold text-white flex items-center gap-2">
              <Film className="w-4 h-4 text-purple-400" />
              Formato de Pantalla & Compensación de Barras Negras (Letterbox)
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Adapta el muestreo para películas y videos panorámicos sin que la tira superior quede apagada.
            </p>
          </div>

          {/* Badge de detección en tiempo real */}
          {isRunning && (
            <div className="flex items-center gap-2 text-xs font-mono bg-[#161a29] px-3 py-1.5 rounded-xl border border-[#22273d] self-start md:self-auto">
              <span className="text-slate-400">Activo:</span>
              <span className="text-purple-400 font-bold">{detectedAspect}</span>
              {cropTopPct > 1 && (
                <span className="text-slate-500 text-[11px]">({cropTopPct}% crop)</span>
              )}
            </div>
          )}
        </div>

        {/* Botones de Selección Rápida */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {/* Automático Adaptativo */}
          <button
            onClick={() => handleAspectRatioChange('auto')}
            className={`p-3.5 rounded-xl flex flex-col gap-1.5 text-left border transition-all duration-150 cursor-pointer ${
              aspect_ratio === 'auto'
                ? 'bg-purple-500/15 border-purple-400 shadow-[0_0_15px_rgba(192,132,252,0.2)]'
                : 'bg-[#161a29] border-[#22273d] hover:border-slate-600 text-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                Automático
              </span>
              <span className="text-[10px] text-purple-400 font-mono bg-purple-500/20 px-1.5 py-0.5 rounded">
                Adaptativo
              </span>
            </div>
            <p className="text-[11px] text-slate-400 leading-snug">
              Detecta barras negras dinámicamente según la carga de CPU.
            </p>
          </button>

          {/* 16:9 Estándar */}
          <button
            onClick={() => handleAspectRatioChange('16:9')}
            className={`p-3.5 rounded-xl flex flex-col gap-1.5 text-left border transition-all duration-150 cursor-pointer ${
              aspect_ratio === '16:9'
                ? 'bg-purple-500/15 border-purple-400 shadow-[0_0_15px_rgba(192,132,252,0.2)]'
                : 'bg-[#161a29] border-[#22273d] hover:border-slate-600 text-slate-300'
            }`}
          >
            <div className="text-xs font-bold text-white">16:9 Completo</div>
            <p className="text-[11px] text-slate-400 leading-snug">
              Bordes físicos externos (Juegos, YouTube y Escritorio).
            </p>
          </button>

          {/* 21:9 Cine */}
          <button
            onClick={() => handleAspectRatioChange('21:9')}
            className={`p-3.5 rounded-xl flex flex-col gap-1.5 text-left border transition-all duration-150 cursor-pointer ${
              aspect_ratio === '21:9'
                ? 'bg-purple-500/15 border-purple-400 shadow-[0_0_15px_rgba(192,132,252,0.2)]'
                : 'bg-[#161a29] border-[#22273d] hover:border-slate-600 text-slate-300'
            }`}
          >
            <div className="text-xs font-bold text-white">21:9 Cine / UltraWide</div>
            <p className="text-[11px] text-slate-400 leading-snug">
              Recorte fijo de ~13% arriba y abajo para películas widescreen.
            </p>
          </button>

          {/* 4:3 Clásico */}
          <button
            onClick={() => handleAspectRatioChange('4:3')}
            className={`p-3.5 rounded-xl flex flex-col gap-1.5 text-left border transition-all duration-150 cursor-pointer ${
              aspect_ratio === '4:3'
                ? 'bg-purple-500/15 border-purple-400 shadow-[0_0_15px_rgba(192,132,252,0.2)]'
                : 'bg-[#161a29] border-[#22273d] hover:border-slate-600 text-slate-300'
            }`}
          >
            <div className="text-xs font-bold text-white">4:3 Retro / Pillarbox</div>
            <p className="text-[11px] text-slate-400 leading-snug">
              Recorte lateral para series clásicas o emuladores retro.
            </p>
          </button>
        </div>
      </div>

      {/* Modular Strip Calibration Card */}
      <div className="bg-[#10131e]/90 border border-[#22273d] rounded-2xl p-5 flex flex-col gap-4 backdrop-blur-md shadow-lg">
        <div className="flex items-center justify-between border-b border-[#22273d]/70 pb-3">
          <div className="text-sm font-bold text-white flex items-center gap-2">
            <Compass className="w-4 h-4 text-purple-400" />
            Orientación y Calibración Modular (3 Tiras)
          </div>
          <div className="flex items-center gap-1.5 text-xs text-purple-400/90 font-mono">
            <Info className="w-3.5 h-3.5" />
            <span>17 LEDs &bull; 29 LEDs &bull; 17 LEDs</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Starting Side */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">
              Lado de Inicio (Conexión / LED #1)
            </label>
            <select
              value={start_side}
              onChange={handleStartSideChange}
              className="bg-[#161a29] border border-[#22273d] text-slate-100 rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-purple-400 transition-colors cursor-pointer"
            >
              <option value="left">Inferior Izquierda &rarr; Arriba &rarr; Baja por Derecha</option>
              <option value="right">Inferior Derecha &rarr; Arriba &rarr; Baja por Izquierda</option>
            </select>
          </div>

          {/* Reverse Sequence */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">
              Invertir Secuencia (Espejo Izq / Der)
            </label>
            <select
              value={String(reverse_order)}
              onChange={handleReverseChange}
              className="bg-[#161a29] border border-[#22273d] text-slate-100 rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-purple-400 transition-colors cursor-pointer"
            >
              <option value="false">Normal</option>
              <option value="true">Invertido (Voltear recorrido de tiras)</option>
            </select>
          </div>

          {/* Fine Tuning Offset */}
          <div className="flex flex-col gap-1.5 md:col-span-2">
            <div className="flex justify-between items-center text-xs font-medium text-slate-400">
              <span>Alineación Fina de Zonas (Offset)</span>
              <span className="text-purple-400 font-bold">{zone_offset >= 0 ? `+${zone_offset}` : zone_offset}</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleOffsetChange(-1)}
                className="w-9 h-9 rounded-lg bg-[#161a29] border border-[#22273d] hover:border-purple-400 hover:text-purple-400 text-slate-200 font-bold flex items-center justify-center transition-all cursor-pointer active:scale-95"
              >
                &minus;
              </button>
              <span className="w-10 text-center font-bold text-sm text-white">{zone_offset}</span>
              <button
                onClick={() => handleOffsetChange(1)}
                className="w-9 h-9 rounded-lg bg-[#161a29] border border-[#22273d] hover:border-purple-400 hover:text-purple-400 text-slate-200 font-bold flex items-center justify-center transition-all cursor-pointer active:scale-95"
              >
                &#43;
              </button>
              <span className="text-[11px] text-slate-400 ml-2">
                Ajusta las zonas hacia adelante o atrás para alinear las esquinas exactas de la pantalla.
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Screen & Image Tuning Card */}
      <div className="bg-[#10131e]/90 border border-[#22273d] rounded-2xl p-5 flex flex-col gap-4 backdrop-blur-md shadow-lg">
        <div className="text-sm font-bold text-white flex items-center gap-2 border-b border-[#22273d]/70 pb-3">
          <Sliders className="w-4 h-4 text-purple-400" />
          Ajustes de Pantalla e Imagen
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Monitor Selection */}
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-400">Monitor a Capturar</label>
              {onRefreshMonitors && (
                <button
                  type="button"
                  onClick={onRefreshMonitors}
                  className="text-[11px] text-purple-400 hover:text-purple-300 flex items-center gap-1 transition-colors cursor-pointer"
                  title="Detectar nuevamente pantallas conectadas"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Refrescar</span>
                </button>
              )}
            </div>
            <select
              value={selectedMonitor}
              onChange={(e) => onSelectMonitor(parseInt(e.target.value, 10))}
              className="bg-[#161a29] border border-[#22273d] text-slate-100 rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-purple-400 transition-colors cursor-pointer"
            >
              {monitors.map((m) => (
                <option key={m.output_idx} value={m.output_idx}>
                  {m.output_name} ({m.resolution[0]}x{m.resolution[1]}) {m.primary ? '[Principal]' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* FPS Target */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">Tasa de Refresco Objetivo</label>
            <select
              value={target_fps}
              onChange={(e) => onUpdateConfig({ target_fps: parseInt(e.target.value, 10) })}
              className="bg-[#161a29] border border-[#22273d] text-slate-100 rounded-lg px-3.5 py-2.5 text-sm outline-none focus:border-purple-400 transition-colors cursor-pointer"
            >
              <option value={30}>30 FPS (Recomendado, consumo ultrabajo)</option>
              <option value={60}>60 FPS (Ultra fluido para Gaming)</option>
            </select>
          </div>

          {/* Smoothing */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-xs font-medium text-slate-400">
              <span>Suavizado de Transición</span>
              <span className="text-purple-400 font-bold">{Number(smoothing).toFixed(2)}</span>
            </div>
            <input
              type="range"
              min="10"
              max="100"
              value={Math.round(smoothing * 100)}
              onChange={(e) => onUpdateConfig({ smoothing: parseFloat(e.target.value) / 100.0 })}
              className="my-1 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>Cine Suave (0.10)</span>
              <span>Gaming Rápido (1.00)</span>
            </div>
          </div>

          {/* Saturation Boost */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-xs font-medium text-slate-400">
              <span>Realce de Saturación</span>
              <span className="text-purple-400 font-bold">{Number(saturation_boost).toFixed(2)}x</span>
            </div>
            <input
              type="range"
              min="100"
              max="200"
              value={Math.round(saturation_boost * 100)}
              onChange={(e) => onUpdateConfig({ saturation_boost: parseFloat(e.target.value) / 100.0 })}
              className="my-1 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>Natural (1.0x)</span>
              <span>Ultra Vibrante (2.0x)</span>
            </div>
          </div>

          {/* Umbral de Corte de Negros */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-xs font-medium text-slate-400">
              <span>Umbral de Corte de Negros</span>
              <span className="text-purple-400 font-bold">{black_cutoff}</span>
            </div>
            <input
              type="range"
              min="0"
              max="40"
              step="1"
              value={black_cutoff}
              onChange={(e) => onUpdateConfig({ black_cutoff: parseInt(e.target.value, 10) })}
              className="my-1 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>Sensible (0)</span>
              <span>Recomendado (15)</span>
              <span>Agresivo (40)</span>
            </div>
          </div>

          {/* Corrección Gamma Óptica */}
          <div className="flex flex-col gap-1.5">
            <div className="flex justify-between items-center text-xs font-medium text-slate-400">
              <span>Corrección Gamma Óptica</span>
              <span className="text-purple-400 font-bold">{Number(gamma).toFixed(1)}</span>
            </div>
            <input
              type="range"
              min="10"
              max="26"
              step="1"
              value={Math.round(gamma * 10)}
              onChange={(e) => onUpdateConfig({ gamma: parseFloat(e.target.value) / 10.0 })}
              className="my-1 cursor-pointer"
            />
            <div className="flex justify-between text-[11px] text-slate-500">
              <span>Lineal (1.0)</span>
              <span>Natural (2.0)</span>
              <span>Profundo (2.6)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
