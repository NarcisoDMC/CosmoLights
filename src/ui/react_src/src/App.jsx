import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Tv,
  Palette,
  Sparkles,
  Power,
  Sun,
  Activity,
  Cpu,
  MonitorCheck,
  Usb,
} from 'lucide-react';
import './App.css';
import MonitorPreview from './components/MonitorPreview';
import AmbilightControls from './components/AmbilightControls';
import SolidColorControls from './components/SolidColorControls';
import EffectsControls from './components/EffectsControls';
import StripBar from './components/StripBar';
import AddStripModal from './components/AddStripModal';
import CosmoLightsLogoHorizontal from './assets/CosmoLightLogo_Horizontal.svg';

// Safe pywebview API bridge invoker
async function callApi(fnName, ...args) {
  if (window.pywebview && window.pywebview.api && window.pywebview.api[fnName]) {
    try {
      return await window.pywebview.api[fnName](...args);
    } catch (err) {
      console.error(`[API] Error calling ${fnName}:`, err);
    }
  }
  return null;
}

export default function App() {
  const [activeTab, setActiveTab] = useState('ambilight');
  const [currentMode, setCurrentMode] = useState('off');
  const [isAmbilightRunning, setIsAmbilightRunning] = useState(false);
  const [isConnected, setIsConnected] = useState(true);
  const [brightness, setBrightness] = useState(100);

  // Multi-Strip Orchestration State (Only real hardware, no mock strips)
  const [strips, setStrips] = useState([]);
  const [activeStripId, setActiveStripId] = useState('strip_1');
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Monitors
  const [monitors, setMonitors] = useState([
    { output_idx: 0, output_name: '\\\\.\\DISPLAY1', resolution: [1920, 1080], primary: true },
  ]);
  const [selectedMonitor, setSelectedMonitor] = useState(0);

  // Custom Effects State
  const [activeEffect, setActiveEffect] = useState('rainbow_flow');
  const [effectSpeed, setEffectSpeed] = useState(1.0);
  const [audioSensitivity, setAudioSensitivity] = useState(1.2);

  // Ambilight Config
  const [config, setConfig] = useState({
    target_fps: 30,
    smoothing: 0.4,
    saturation_boost: 1.25,
    border_depth: 0.08,
    start_side: 'left',
    reverse_order: false,
    zone_offset: 0,
    aspect_ratio: 'auto',
    black_cutoff: 15,
    gamma: 2.0,
  });

  // Telemetry stats
  const [stats, setStats] = useState({
    fps: 0.0,
    frames_processed: 0,
    detected_aspect: '16:9',
    crop_top_pct: 0,
    led_preview: Array(34).fill([0, 0, 0]),
  });

  // Ref to prevent overlapping polling intervals
  const isPolling = useRef(false);

  // Initialize connection
  useEffect(() => {
    async function init() {
      const data = await callApi('initialize');
      if (data) {
        setIsConnected(data.connected);
        if (data.monitors && data.monitors.length > 0) {
          setMonitors(data.monitors);
        }
        if (data.selected_monitor !== undefined) {
          setSelectedMonitor(data.selected_monitor);
        }
        if (data.strips && data.strips.length > 0) {
          setStrips(data.strips);
        }
        if (data.active_strip_id) {
          setActiveStripId(data.active_strip_id);
        }
        if (data.config) {
          setConfig((prev) => ({ ...prev, ...data.config }));
          if (data.config.brightness !== undefined) {
            setBrightness(data.config.brightness);
          }
        }
        if (data.last_effect_id) {
          setActiveEffect(data.last_effect_id);
        }
        if (data.effect_speed !== undefined) {
          setEffectSpeed(data.effect_speed);
        }
        if (data.audio_sensitivity !== undefined) {
          setAudioSensitivity(data.audio_sensitivity);
        }
        if (data.current_mode) {
          setCurrentMode(data.current_mode);
        }
      }
    }

    if (window.pywebview) {
      init();
    } else {
      window.addEventListener('pywebviewready', init, { once: true });
    }
  }, []);

  // Telemetry Polling (10 Hz)
  useEffect(() => {
    const timer = setInterval(async () => {
      if (isPolling.current) return;
      isPolling.current = true;

      try {
        const live = await callApi('get_stats');
        if (live) {
          setStats((prev) => ({
            ...prev,
            fps: live.fps || 0.0,
            frames_processed: live.frames_processed || 0,
            detected_aspect: live.detected_aspect || prev.detected_aspect,
            crop_top_pct: live.crop_top_pct ?? prev.crop_top_pct,
            led_preview: live.led_preview || prev.led_preview,
          }));
          setIsConnected(live.connected ?? isConnected);

          const ambilightActive = Boolean(
            (live.is_ambilight_running ?? live.running) && live.current_mode === 'ambilight'
          );
          setIsAmbilightRunning(ambilightActive);

          if (live.current_mode) {
            setCurrentMode(live.current_mode);
          }

          if (live.strips && Array.isArray(live.strips)) {
            setStrips(live.strips);
          }
          if (live.active_strip_id && live.active_strip_id !== activeStripId) {
            setActiveStripId(live.active_strip_id);
          }
        }
      } finally {
        isPolling.current = false;
      }
    }, 100);

    return () => clearInterval(timer);
  }, [isConnected, activeStripId]);

  // Handler: Select Active Strip
  const handleSelectStrip = useCallback(async (stripId) => {
    setActiveStripId(stripId);
    const res = await callApi('set_active_strip', stripId);
    if (res && res.state) {
      const s = res.state;
      setCurrentMode(s.mode || 'off');
      setIsConnected(Boolean(s.connected));
      setIsAmbilightRunning(s.mode === 'ambilight');
      if (s.brightness !== undefined) {
        setBrightness(s.brightness);
      }
      if (s.config) {
        setConfig((prev) => ({ ...prev, ...s.config }));
        if (s.config.selected_monitor !== undefined) {
          setSelectedMonitor(s.config.selected_monitor);
        }
      }
      if (s.active_effect) {
        setActiveEffect(s.active_effect);
      }
      if (s.effect_speed !== undefined) {
        setEffectSpeed(s.effect_speed);
      }
      if (s.audio_sensitivity !== undefined) {
        setAudioSensitivity(s.audio_sensitivity);
      }
      if (s.led_preview) {
        setStats((prev) => ({ ...prev, led_preview: s.led_preview }));
      }
    }
  }, []);

  // Handler: Add New Strip
  const handleAddStrip = useCallback(
    async (stripData) => {
      const res = await callApi(
        'add_strip',
        stripData.name,
        stripData.device_type,
        stripData.device_index,
        stripData.port,
        stripData.total_leds,
        stripData.selected_monitor
      );
      if (res && res.strips) {
        setStrips(res.strips);
        if (res.strip) {
          await handleSelectStrip(res.strip.id);
        }
      }
    },
    [handleSelectStrip]
  );

  // Handler: Remove Strip
  const handleRemoveStrip = useCallback(
    async (stripId) => {
      const res = await callApi('remove_strip', stripId);
      if (res && res.strips) {
        setStrips(res.strips);
        if (res.active_strip_id) {
          await handleSelectStrip(res.active_strip_id);
        }
      }
    },
    [handleSelectStrip]
  );

  // Handler: Rename Strip
  const handleRenameStrip = useCallback(async (stripId, newName) => {
    const res = await callApi('rename_strip', stripId, newName);
    if (res && res.success) {
      setStrips((prev) =>
        prev.map((s) => (s.id === stripId ? { ...s, name: res.name || newName } : s))
      );
    }
  }, []);

  // Handler: Master Power Off (All Strips)
  const handleTurnOffAll = useCallback(async () => {
    await callApi('turn_off_all');
    setIsAmbilightRunning(false);
    setCurrentMode('off');
    setStats((prev) => ({
      ...prev,
      led_preview: Array(34).fill([0, 0, 0]),
    }));
    setStrips((prev) => prev.map((s) => ({ ...s, mode: 'off' })));
  }, []);

  // Handler: Toggle Ambilight for Active Strip
  const handleToggleAmbilight = useCallback(async () => {
    const nextState = !isAmbilightRunning;
    setIsAmbilightRunning(nextState);
    setCurrentMode(nextState ? 'ambilight' : 'off');
    await callApi('toggle_ambilight', nextState);
  }, [isAmbilightRunning]);

  // Handler: Update Config for Active Strip
  const handleUpdateConfig = useCallback(async (newProps) => {
    setConfig((prev) => {
      const updated = { ...prev, ...newProps };
      if (
        'start_side' in newProps ||
        'reverse_order' in newProps ||
        'zone_offset' in newProps
      ) {
        callApi(
          'set_orientation',
          updated.start_side,
          updated.reverse_order,
          updated.zone_offset
        );
      } else {
        callApi('update_config', newProps);
      }
      return updated;
    });
  }, []);

  // Handler: Select Monitor for Active Strip
  const handleSelectMonitor = useCallback(async (outputIdx) => {
    setSelectedMonitor(outputIdx);
    await callApi('set_monitor', outputIdx);
  }, []);

  // Handler: Refresh Connected Monitors
  const handleRefreshMonitors = useCallback(async () => {
    const list = await callApi('list_monitors');
    if (list && list.length > 0) {
      setMonitors(list);
      if (!list.some((m) => m.output_idx === selectedMonitor)) {
        const nextId = list[0].output_idx;
        setSelectedMonitor(nextId);
        await callApi('set_monitor', nextId);
      }
    }
  }, [selectedMonitor]);

  const brightnessThrottle = useRef(null);
  const lastBrightnessTime = useRef(0);

  // Handler: Brightness Change (Active Strip)
  const handleBrightnessChange = useCallback((e) => {
    const val = parseInt(e.target.value, 10);
    setBrightness(val);

    if (brightnessThrottle.current) {
      clearTimeout(brightnessThrottle.current);
    }

    const now = Date.now();
    if (now - lastBrightnessTime.current > 50) {
      lastBrightnessTime.current = now;
      callApi('set_brightness', val);
    } else {
      brightnessThrottle.current = setTimeout(() => {
        lastBrightnessTime.current = Date.now();
        callApi('set_brightness', val);
      }, 50);
    }
  }, []);

  // Handler: Solid Color for Active Strip
  const handleSetSolidColor = useCallback(async (r, g, b) => {
    setIsAmbilightRunning(false);
    setCurrentMode('solid');
    setStats((prev) => ({
      ...prev,
      led_preview: Array(34).fill([r, g, b]),
    }));
    await callApi('set_solid_color', r, g, b);
  }, []);

  // Handler: Custom Software Effect & Audio for Active Strip
  const handleSetEffect = useCallback(
    async (effectId) => {
      setActiveEffect(effectId);
      setIsAmbilightRunning(false);
      setCurrentMode('effect');
      await callApi('set_custom_effect', effectId, effectSpeed);
    },
    [effectSpeed]
  );

  const handleSetSpeed = useCallback(async (newSpeed) => {
    setEffectSpeed(newSpeed);
    await callApi('set_effect_speed', newSpeed);
  }, []);

  const handleSetSensitivity = useCallback(async (newSens) => {
    setAudioSensitivity(newSens);
    await callApi('set_audio_sensitivity', newSens);
  }, []);

  // Handler: Power Off Active Strip
  const handleTurnOff = useCallback(async () => {
    setIsAmbilightRunning(false);
    setCurrentMode('off');
    setStats((prev) => ({
      ...prev,
      led_preview: Array(34).fill([0, 0, 0]),
    }));
    await callApi('turn_off');
  }, []);

  const activeMonitorObj =
    monitors.find((m) => m.output_idx === selectedMonitor) || monitors[0];
  const activeStripObj =
    strips.find((s) => s.id === activeStripId) || strips[0] || null;

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-[#080a10] text-slate-100 select-none">
      {/* Top Header Bar */}
      <header className="bg-[#10131e]/90 border-b border-[#22273d] px-6 py-2.5 flex items-center justify-between backdrop-blur-md shrink-0">
        <div className="flex items-center gap-3">
          <div>
            <img src={CosmoLightsLogoHorizontal} alt="CosmoLights Logo" className="h-16 w-auto" />
            <div className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">
              Real-Time Ambilight Controller
            </div>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Active Strip Brightness */}
          <div className="flex items-center gap-2.5 bg-[#161a29] px-3.5 py-1.5 rounded-full border border-[#22273d] text-xs">
            <Sun className="w-4 h-4 text-purple-400 shrink-0" />
            <span className="text-slate-400 font-medium">Brillo:</span>
            <input
              type="range"
              min="0"
              max="100"
              value={brightness}
              onChange={handleBrightnessChange}
              className="w-24 cursor-pointer"
            />
            <span className="font-bold text-white min-w-9">{brightness}%</span>
          </div>

          {/* Active Strip Hardware Badge */}
          <div className="flex items-center gap-2 bg-[#161a29] px-3.5 py-1.5 rounded-full border border-[#22273d] text-xs font-medium">
            <span
              className={`w-2 h-2 rounded-full ${
                isConnected
                  ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
                  : 'bg-rose-500 shadow-[0_0_8px_#f43f5e]'
              }`}
            />
            <span className="text-slate-300">
              {isConnected
                ? activeStripObj?.driver_type === 'serial'
                  ? `Serial COM (${activeStripObj.port || 'Adalight'})`
                  : 'QinHeng 1A86:FE07'
                : 'Desconectado'}
            </span>
          </div>
        </div>
      </header>

      {/* Multi-Strip Selector Bar */}
      <StripBar
        strips={strips}
        activeStripId={activeStripId}
        onSelectStrip={handleSelectStrip}
        onAddClick={() => setIsAddModalOpen(true)}
        onTurnOffAll={handleTurnOffAll}
        onRemoveStrip={handleRemoveStrip}
        onRenameStrip={handleRenameStrip}
      />

      {/* Main Layout Area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Navigation Sidebar */}
        <aside className="w-56 bg-[#10131e]/90 border-r border-[#22273d] p-4 flex flex-col gap-2 shrink-0 backdrop-blur-md">
          <button
            onClick={() => setActiveTab('ambilight')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-150 cursor-pointer ${
              activeTab === 'ambilight'
                ? 'text-purple-400 bg-purple-400/10 border border-purple-400/30 shadow-[0_0_15px_rgba(192, 132, 252,0.1)]'
                : 'text-slate-400 hover:text-white hover:bg-[#161a29] border border-transparent'
            }`}
          >
            <Tv className="w-4 h-4" />
            <span>Ambilight</span>
          </button>

          <button
            onClick={() => setActiveTab('solid')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-150 cursor-pointer ${
              activeTab === 'solid'
                ? 'text-purple-400 bg-purple-400/10 border border-purple-400/30 shadow-[0_0_15px_rgba(192, 132, 252,0.1)]'
                : 'text-slate-400 hover:text-white hover:bg-[#161a29] border border-transparent'
            }`}
          >
            <Palette className="w-4 h-4" />
            <span>Color Fijo</span>
          </button>

          <button
            onClick={() => setActiveTab('effects')}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all duration-150 cursor-pointer ${
              activeTab === 'effects'
                ? 'text-purple-400 bg-purple-400/10 border border-purple-400/30 shadow-[0_0_15px_rgba(192, 132, 252,0.1)]'
                : 'text-slate-400 hover:text-white hover:bg-[#161a29] border border-transparent'
            }`}
          >
            <Sparkles className="w-4 h-4" />
            <span>Efectos</span>
          </button>

          {/* Turn Off Active Strip Button */}
          <button
            onClick={handleTurnOff}
            className="mt-auto w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold text-rose-500 hover:text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 hover:border-rose-500/40 transition-all duration-150 cursor-pointer active:scale-95"
            title="Apagar tira activa"
          >
            <Power className="w-4 h-4" />
            <span>Apagar Tira</span>
          </button>
        </aside>

        {/* Dynamic Main Workspace */}
        <main className="flex-1 overflow-y-auto p-8 flex flex-col gap-6">
          {/* Virtual Monitor with 34 LED dots */}
          <MonitorPreview
            mode={currentMode}
            resolution={
              activeMonitorObj
                ? `${activeMonitorObj.resolution[0]}x${activeMonitorObj.resolution[1]}`
                : '1920x1080'
            }
            monitorName={activeMonitorObj?.output_name}
            ledColors={stats.led_preview}
            isRunning={isAmbilightRunning}
          />

          {/* Active Tab View */}
          {activeTab === 'ambilight' && (
            <AmbilightControls
              isRunning={isAmbilightRunning}
              onToggle={handleToggleAmbilight}
              config={config}
              onUpdateConfig={handleUpdateConfig}
              monitors={monitors}
              selectedMonitor={selectedMonitor}
              onSelectMonitor={handleSelectMonitor}
              onRefreshMonitors={handleRefreshMonitors}
              detectedAspect={stats.detected_aspect}
              cropTopPct={stats.crop_top_pct}
            />
          )}

          {activeTab === 'solid' && (
            <SolidColorControls onSetColor={handleSetSolidColor} />
          )}

          {activeTab === 'effects' && (
            <EffectsControls
              activeEffect={activeEffect}
              onSetEffect={handleSetEffect}
              speed={effectSpeed}
              onSetSpeed={handleSetSpeed}
              sensitivity={audioSensitivity}
              onSetSensitivity={handleSetSensitivity}
            />
          )}
        </main>
      </div>

      {/* Bottom Telemetry Bar */}
      <footer className="bg-[#10131e]/90 border-t border-[#22273d] px-6 py-2.5 flex items-center justify-between text-xs text-slate-400 shrink-0 backdrop-blur-md">
        <div className="flex items-center gap-2">
          <span>Tira Activa:</span>
          <strong className="text-white font-semibold">
            {activeStripObj?.name || 'Tira Principal'}
          </strong>
          <span className="text-slate-600">|</span>
          <span>Modo:</span>
          <strong className="text-purple-300 font-semibold">
            {currentMode === 'ambilight'
              ? 'Ambilight Pantalla'
              : currentMode === 'solid'
              ? 'Color Fijo'
              : currentMode === 'effect'
              ? `Efecto: ${activeEffect}`
              : 'En Reposo'}
          </strong>
        </div>

        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-purple-400" />
          <span>FPS:</span>
          <strong className="text-white font-semibold">{stats.fps.toFixed(1)}</strong>
        </div>

        <div className="flex items-center gap-2">
          <Cpu className="w-3.5 h-3.5 text-purple-400" />
          <span>Cuadros Sincronizados:</span>
          <strong className="text-white font-semibold">{stats.frames_processed}</strong>
        </div>

        <div className="flex items-center gap-2">
          <MonitorCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Salida:</span>
          <strong className="text-white font-semibold">
            {activeMonitorObj?.output_name || 'DISPLAY1'}
          </strong>
        </div>
      </footer>

      {/* Add Strip Modal */}
      <AddStripModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={handleAddStrip}
        existingStrips={strips}
        monitors={monitors}
        callApi={callApi}
      />
    </div>
  );
}
