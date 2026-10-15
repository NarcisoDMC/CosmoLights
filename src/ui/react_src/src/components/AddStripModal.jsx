import React, { useState, useEffect, useCallback } from 'react';
import {
  X,
  Plus,
  Usb,
  Cpu,
  RefreshCw,
  AlertCircle,
  Tv,
  Layers,
  Sparkles,
  CheckCircle2,
} from 'lucide-react';

export default function AddStripModal({
  isOpen,
  onClose,
  onAdd,
  existingStrips = [],
  monitors = [],
  callApi,
}) {
  const [loading, setLoading] = useState(false);
  const [hw, setHw] = useState({ qinheng: [], serial: [] });
  const [selectedDevice, setSelectedDevice] = useState(null);
  const [name, setName] = useState('');
  const [totalLeds, setTotalLeds] = useState(63);
  const [selectedMonitor, setSelectedMonitor] = useState(0);
  const [errorMsg, setErrorMsg] = useState('');

  // Discover real hardware
  const scanHardware = useCallback(async () => {
    setLoading(true);
    setErrorMsg('');
    try {
      const res = await callApi('enumerate_hardware');
      if (res) {
        setHw({
          qinheng: Array.isArray(res.qinheng) ? res.qinheng : [],
          serial: Array.isArray(res.serial) ? res.serial : [],
        });
      }
    } catch (err) {
      console.error('[AddStripModal] Error enumerating hardware:', err);
      setErrorMsg('Error al escanear los puertos y dispositivos.');
    } finally {
      setLoading(false);
    }
  }, [callApi]);

  useEffect(() => {
    if (isOpen) {
      scanHardware();
      setName(`Tira LED ${existingStrips.length + 1}`);
      setTotalLeds(63);
      setSelectedMonitor(monitors[0]?.output_idx ?? 0);
      setSelectedDevice(null);
    }
  }, [isOpen, scanHardware, existingStrips.length, monitors]);

  if (!isOpen) return null;

  // Filter out devices already assigned to existing strips
  const assignedQinHengIndices = new Set(
    existingStrips
      .filter((s) => s.driver_type === 'qinheng')
      .map((s) => s.device_index ?? 0)
  );

  const assignedSerialPorts = new Set(
    existingStrips
      .filter((s) => s.driver_type === 'serial')
      .map((s) => s.port)
  );

  const availableDevices = [];

  // QinHeng USB controllers
  hw.qinheng.forEach((dev) => {
    const isAssigned = assignedQinHengIndices.has(dev.index);
    if (!isAssigned) {
      availableDevices.push({
        id: `qinheng_${dev.index}`,
        type: 'qinheng',
        device_index: dev.index,
        label: `QinHeng USB Controller (Bus ${dev.bus}, Disp ${dev.address})`,
        detail: dev.device_name || 'VID: 1A86, PID: FE07',
      });
    }
  });

  // Serial COM Ports (Adalight / Arduino / ESP32)
  hw.serial.forEach((sp) => {
    const isAssigned = assignedSerialPorts.has(sp.port);
    if (!isAssigned) {
      availableDevices.push({
        id: `serial_${sp.port}`,
        type: 'serial',
        port: sp.port,
        label: `Puerto ${sp.port} (${sp.description || 'Dispositivo Serial / Adalight'})`,
        detail: sp.hwid ? `HWID: ${sp.hwid}` : 'Compatible con protocolo Adalight',
      });
    }
  });

  // Auto-select first available if none selected
  const activeDevice =
    selectedDevice || (availableDevices.length > 0 ? availableDevices[0] : null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!activeDevice) return;

    if (!name.trim()) {
      setErrorMsg('Por favor especifica un nombre para la tira.');
      return;
    }

    const payload = {
      name: name.trim(),
      device_type: activeDevice.type,
      device_index: activeDevice.device_index ?? 0,
      port: activeDevice.port ?? 'COM3',
      total_leds: parseInt(totalLeds, 10) || 63,
      selected_monitor: parseInt(selectedMonitor, 10) || 0,
    };

    setLoading(true);
    try {
      await onAdd(payload);
      onClose();
    } catch (err) {
      setErrorMsg('Error al agregar el dispositivo: ' + String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="bg-[#10131e] border border-[#262c44] rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-[#22273d] flex items-center justify-between bg-[#151927]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-400">
              <Plus className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Añadir Tira LED</h2>
              <p className="text-xs text-slate-400">
                Detecta y vincula un controlador físico secundario
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#22273d] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body Content */}
        <div className="p-6 flex flex-col gap-5 overflow-y-auto max-h-[75vh]">
          {errorMsg && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Device Detection Section */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Dispositivos Físicos Detectados:
              </label>
              <button
                type="button"
                onClick={scanHardware}
                disabled={loading}
                className="flex items-center gap-1.5 text-xs text-purple-400 hover:text-purple-300 disabled:opacity-50 cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                <span>{loading ? 'Buscando...' : 'Escanear'}</span>
              </button>
            </div>

            {loading ? (
              <div className="py-8 flex flex-col items-center justify-center gap-3 text-slate-400 border border-dashed border-[#22273d] rounded-xl bg-[#0c0e17]">
                <RefreshCw className="w-6 h-6 animate-spin text-purple-400" />
                <span className="text-xs">Escaneando buses USB y puertos COM...</span>
              </div>
            ) : availableDevices.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-[#2b3350] bg-[#0c0e17] flex flex-col gap-3">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
                  <div className="text-xs text-slate-300 flex flex-col gap-1">
                    <strong className="text-amber-300 font-semibold">
                      No se detectaron controladores adicionales disponibles
                    </strong>
                    <p className="text-slate-400 leading-relaxed">
                      Todos los controladores conectados ya están en uso, o no hay ningún otro
                      hardware USB (QinHeng) ni puerto COM (Arduino / ESP32 Adalight) conectado al
                      equipo.
                    </p>
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 bg-[#161a2b] p-3 rounded-lg border border-[#22273d] space-y-1">
                  <div className="font-semibold text-slate-300">¿Cómo conectar una segunda tira?</div>
                  <div>
                    • <strong>QinHeng USB:</strong> Conecta un segundo controlador USB idéntico.
                  </div>
                  <div>
                    • <strong>Arduino / ESP32:</strong> Conecta tu placa por USB y asegúrate de que
                    tenga cargado el firmware Adalight.
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {availableDevices.map((dev) => {
                  const isSelected = activeDevice?.id === dev.id;
                  return (
                    <div
                      key={dev.id}
                      onClick={() => setSelectedDevice(dev)}
                      className={`p-3 rounded-xl border flex items-center justify-between cursor-pointer transition-all ${
                        isSelected
                          ? 'bg-purple-950/40 border-purple-500/60 shadow-[0_0_12px_rgba(168,85,247,0.2)] text-white'
                          : 'bg-[#151927] border-[#22273d] text-slate-300 hover:border-slate-600'
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`p-2 rounded-lg ${
                            dev.type === 'serial'
                              ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                              : 'bg-purple-500/10 text-purple-400 border border-purple-500/30'
                          }`}
                        >
                          {dev.type === 'serial' ? (
                            <Cpu className="w-4 h-4" />
                          ) : (
                            <Usb className="w-4 h-4" />
                          )}
                        </div>
                        <div>
                          <div className="text-xs font-semibold">{dev.label}</div>
                          <div className="text-[10px] text-slate-400">{dev.detail}</div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {isSelected && (
                          <CheckCircle2 className="w-4 h-4 text-purple-400 shrink-0" />
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Form Fields (Only active when devices are available) */}
          {availableDevices.length > 0 && (
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {/* Name */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-slate-300">Nombre de la Tira:</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Ej: Tira Monitor 2, Luz Superior..."
                  className="bg-[#0b0d14] border border-[#22273d] focus:border-purple-500/60 rounded-xl px-3.5 py-2 text-xs text-white outline-none"
                  required
                />
              </div>

              {/* Total LEDs */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-slate-300">
                  Cantidad de LEDs en la tira:
                </label>
                <input
                  type="number"
                  min="1"
                  max="500"
                  value={totalLeds}
                  onChange={(e) => setTotalLeds(e.target.value)}
                  className="bg-[#0b0d14] border border-[#22273d] focus:border-purple-500/60 rounded-xl px-3.5 py-2 text-xs text-white outline-none"
                />
                <span className="text-[10px] text-slate-500">
                  Por defecto son 63 LEDs para el controlador estándar QinHeng.
                </span>
              </div>

              {/* Target Monitor */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <Tv className="w-3.5 h-3.5 text-purple-400" />
                  <span>Pantalla de Muestreo (Ambilight):</span>
                </label>
                <select
                  value={selectedMonitor}
                  onChange={(e) => setSelectedMonitor(Number(e.target.value))}
                  className="bg-[#0b0d14] border border-[#22273d] focus:border-purple-500/60 rounded-xl px-3.5 py-2 text-xs text-white outline-none cursor-pointer"
                >
                  {monitors.map((m) => (
                    <option key={m.output_idx} value={m.output_idx}>
                      Monitor {m.output_idx + 1}: {m.resolution[0]}x{m.resolution[1]}{' '}
                      {m.primary ? '(Principal)' : ''}
                    </option>
                  ))}
                </select>
                <span className="text-[10px] text-slate-500">
                  Cada tira puede capturar una pantalla distinta o compartir la misma pantalla.
                </span>
              </div>

              {/* Actions */}
              <div className="pt-2 flex items-center justify-end gap-3 border-t border-[#22273d]">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-[#1a2033] border border-transparent transition-colors cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={loading || !activeDevice}
                  className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-[0_0_15px_rgba(168,85,247,0.3)] transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>{loading ? 'Agregando...' : 'Añadir y Conectar Tira'}</span>
                </button>
              </div>
            </form>
          )}

          {availableDevices.length === 0 && !loading && (
            <div className="pt-2 flex items-center justify-end border-t border-[#22273d]">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white hover:bg-[#1a2033] border border-[#22273d] transition-colors cursor-pointer"
              >
                Cerrar
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
