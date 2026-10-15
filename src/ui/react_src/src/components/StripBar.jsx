import React, { useState } from 'react';
import { Plus, Power, Trash2, Edit2, Check, X, Usb, Cpu, Sparkles } from 'lucide-react';

export default function StripBar({
  strips = [],
  activeStripId,
  onSelectStrip,
  onAddClick,
  onTurnOffAll,
  onRemoveStrip,
  onRenameStrip,
}) {
  const [editingId, setEditingId] = useState(null);
  const [editName, setEditName] = useState('');

  const handleStartRename = (strip, e) => {
    e.stopPropagation();
    setEditingId(strip.id);
    setEditName(strip.name);
  };

  const handleSaveRename = (stripId, e) => {
    e.stopPropagation();
    if (editName.trim()) {
      onRenameStrip(stripId, editName.trim());
    }
    setEditingId(null);
  };

  const handleCancelRename = (e) => {
    e.stopPropagation();
    setEditingId(null);
  };

  const handleKeyDown = (stripId, e) => {
    if (e.key === 'Enter') {
      handleSaveRename(stripId, e);
    } else if (e.key === 'Escape') {
      handleCancelRename(e);
    }
  };

  return (
    <div className="bg-[#0e111b] border-b border-[#1f2438] px-6 py-2.5 flex items-center justify-between gap-4 overflow-x-auto shrink-0 select-none backdrop-blur-md">
      {/* Strip Selector Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto py-1 scrollbar-none">
        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mr-1 shrink-0">
          Tiras:
        </span>

        {strips.map((strip) => {
          const isActive = strip.id === activeStripId;
          const isConnected = strip.connected;
          const isEditing = editingId === strip.id;

          return (
            <div
              key={strip.id}
              onClick={() => onSelectStrip(strip.id)}
              className={`group flex items-center gap-2.5 px-3 py-1.5 rounded-xl border text-xs font-medium cursor-pointer transition-all duration-200 shrink-0 ${
                isActive
                  ? 'bg-purple-950/40 border-purple-500/50 text-white shadow-[0_0_12px_rgba(168,85,247,0.2)]'
                  : 'bg-[#151826]/70 border-[#22273d] text-slate-400 hover:text-slate-200 hover:bg-[#1a2033] hover:border-slate-700'
              }`}
            >
              {/* Connection Status Indicator */}
              <span
                className={`w-2 h-2 rounded-full shrink-0 transition-all ${
                  isConnected
                    ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]'
                    : 'bg-rose-500 shadow-[0_0_6px_#f43f5e]'
                }`}
                title={isConnected ? 'Controlador Conectado' : 'Controlador Desconectado'}
              />

              {/* Hardware / Driver Type Badge */}
              <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-md font-mono bg-[#1c2236] text-slate-300 border border-[#2a324b]">
                {strip.driver_type === 'serial' ? (
                  <>
                    <Cpu className="w-3 h-3 text-cyan-400" />
                    <span>COM</span>
                  </>
                ) : (
                  <>
                    <Usb className="w-3 h-3 text-purple-400" />
                    <span>USB</span>
                  </>
                )}
              </span>

              {/* Strip Name (Editable or Read-only) */}
              {isEditing ? (
                <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(strip.id, e)}
                    className="bg-[#0b0d14] text-white border border-purple-500/60 rounded px-1.5 py-0.5 text-xs outline-none w-28"
                    autoFocus
                  />
                  <button
                    onClick={(e) => handleSaveRename(strip.id, e)}
                    className="p-0.5 text-emerald-400 hover:text-emerald-300"
                    title="Guardar nombre"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={handleCancelRename}
                    className="p-0.5 text-slate-400 hover:text-slate-300"
                    title="Cancelar"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5">
                  <span className={`font-semibold ${isActive ? 'text-white' : 'text-slate-300'}`}>
                    {strip.name}
                  </span>
                  <button
                    onClick={(e) => handleStartRename(strip, e)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 text-slate-400 hover:text-purple-300"
                    title="Renombrar tira"
                  >
                    <Edit2 className="w-3 h-3" />
                  </button>
                </div>
              )}

              {/* Current Mode Badge */}
              <span
                className={`text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded font-bold ${
                  strip.mode === 'ambilight'
                    ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30'
                    : strip.mode === 'solid'
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                    : strip.mode === 'effect'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {strip.mode === 'ambilight'
                  ? 'Ambi'
                  : strip.mode === 'solid'
                  ? 'Color'
                  : strip.mode === 'effect'
                  ? 'Efecto'
                  : 'Off'}
              </span>

              {/* Remove Secondary Strip Button (Only when more than 1 strip and not strip_1) */}
              {strips.length > 1 && strip.id !== 'strip_1' && !isEditing && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`¿Eliminar la tira "${strip.name}"?`)) {
                      onRemoveStrip(strip.id);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 transition-opacity p-0.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded"
                  title="Eliminar tira"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Right Controls: Add Strip & Master Power Off */}
      <div className="flex items-center gap-2.5 shrink-0">
        <button
          onClick={onAddClick}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 hover:text-purple-200 border border-purple-500/40 hover:border-purple-500/60 transition-all duration-150 cursor-pointer shadow-[0_0_10px_rgba(168,85,247,0.15)] active:scale-95"
          title="Detectar y añadir una nueva tira LED física"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Añadir Tira</span>
        </button>

        <button
          onClick={onTurnOffAll}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-rose-600/15 hover:bg-rose-600/25 text-rose-400 hover:text-rose-300 border border-rose-500/30 hover:border-rose-500/50 transition-all duration-150 cursor-pointer active:scale-95"
          title="Apagar todas las tiras configuradas al mismo tiempo"
        >
          <Power className="w-3.5 h-3.5" />
          <span>Apagar Todo</span>
        </button>
      </div>
    </div>
  );
}
