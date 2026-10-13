import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Palette, Pipette, Sun } from 'lucide-react';

const PRESETS = [
  { name: 'Rojo Neón', hex: '#ff0000', rgb: [255, 0, 0] },
  { name: 'Verde Matrix', hex: '#00ff00', rgb: [0, 255, 0] },
  { name: 'Azul Eléctrico', hex: '#0066ff', rgb: [0, 102, 255] },
  { name: 'Cyan Cyberpunk', hex: '#00f0ff', rgb: [0, 240, 255] },
  { name: 'Ámbar Cálido', hex: '#ffaa00', rgb: [255, 170, 0] },
  { name: 'Blanco Cálido 3000K', hex: '#ffb464', rgb: [255, 180, 100] },
  { name: 'Blanco Puro 6500K', hex: '#ffffff', rgb: [255, 255, 255] },
  { name: 'Púrpura Neon', hex: '#a855f7', rgb: [168, 85, 247] },
  { name: 'Rosa Magenta', hex: '#ec4899', rgb: [236, 72, 153] },
  { name: 'Amarillo Neón', hex: '#eab308', rgb: [234, 179, 8] },
];

const WHEEL_SIZE = 232; // px (CSS)
const SEND_INTERVAL_MS = 40; // máx. ~25 actualizaciones/s hacia el hardware

// ---------------------------------------------------------------------------
// Conversión de color
// ---------------------------------------------------------------------------
function hsvToRgb(h, s, v) {
  const c = v * s;
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  const m = v - c;
  let r = 0, g = 0, b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
}

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const d = max - min;
  let h = 0;
  if (d !== 0) {
    if (max === r) h = 60 * (((g - b) / d) % 6);
    else if (max === g) h = 60 * ((b - r) / d + 2);
    else h = 60 * ((r - g) / d + 4);
  }
  if (h < 0) h += 360;
  return { h, s: max === 0 ? 0 : d / max, v: max };
}

const toHex = (rgb) => '#' + rgb.map((c) => c.toString(16).padStart(2, '0')).join('');

function parseHex(value) {
  const m = /^#?([0-9a-f]{6})$/i.exec(value.trim());
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// ---------------------------------------------------------------------------
// Rueda cromática (canvas)
// ---------------------------------------------------------------------------
function ColorWheel({ hsv, onChange, onCommit }) {
  const canvasRef = useRef(null);
  const draggingRef = useRef(false);
  const radius = WHEEL_SIZE / 2;

  // Dibuja tono (ángulo) + saturación (radio) una sola vez
  useEffect(() => {
    const canvas = canvasRef.current;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = WHEEL_SIZE * dpr;
    canvas.height = WHEEL_SIZE * dpr;
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    const hue = ctx.createConicGradient(0, radius, radius);
    for (let i = 0; i <= 12; i++) {
      hue.addColorStop(i / 12, `hsl(${i * 30}, 100%, 50%)`);
    }
    ctx.beginPath();
    ctx.arc(radius, radius, radius, 0, Math.PI * 2);
    ctx.fillStyle = hue;
    ctx.fill();

    const sat = ctx.createRadialGradient(radius, radius, 0, radius, radius, radius);
    sat.addColorStop(0, 'rgba(255,255,255,1)');
    sat.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = sat;
    ctx.fill();
  }, [radius]);

  const pick = useCallback(
    (e) => {
      const rect = canvasRef.current.getBoundingClientRect();
      const r = rect.width / 2;
      const dx = e.clientX - rect.left - r;
      const dy = e.clientY - rect.top - r;
      const h = ((Math.atan2(dy, dx) * 180) / Math.PI + 360) % 360;
      const s = Math.min(1, Math.hypot(dx, dy) / r);
      onChange({ h, s });
    },
    [onChange]
  );

  const handleDown = (e) => {
    draggingRef.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
    pick(e);
  };
  const handleMove = (e) => draggingRef.current && pick(e);
  const handleUp = (e) => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    e.currentTarget.releasePointerCapture(e.pointerId);
    onCommit();
  };

  const angle = (hsv.h * Math.PI) / 180;
  const RING = 3; // grosor del aro degradado (p-[3px])
  const inner = radius - RING;
  const thumbX = radius + Math.cos(angle) * hsv.s * inner;
  const thumbY = radius + Math.sin(angle) * hsv.s * inner;
  const thumbColor = toHex(hsvToRgb(hsv.h, hsv.s, hsv.v));

  return (
    <div className="relative shrink-0" style={{ width: WHEEL_SIZE, height: WHEEL_SIZE }}>
      {/* Halo exterior con el color actual */}
      <div
        className="absolute -inset-3 rounded-full blur-2xl opacity-40 transition-colors duration-200 pointer-events-none"
        style={{ backgroundColor: thumbColor }}
      />
      <div
        className="relative w-full h-full rounded-full p-[3px] bg-gradient-to-br from-purple-400/60 via-[#22273d] to-indigo-500/60 shadow-[0_0_25px_rgba(192,132,252,0.15)]"
      >
        <div
          className="relative w-full h-full rounded-full overflow-hidden cursor-crosshair touch-none"
          onPointerDown={handleDown}
          onPointerMove={handleMove}
          onPointerUp={handleUp}
          onPointerCancel={handleUp}
        >
          <canvas ref={canvasRef} className="w-full h-full block" />
          {/* Capa de brillo (valor HSV) */}
          <div
            className="absolute inset-0 bg-black pointer-events-none"
            style={{ opacity: 1 - hsv.v }}
          />
        </div>
      </div>
      {/* Selector */}
      <div
        className="absolute w-6 h-6 -ml-3 -mt-3 rounded-full border-[3px] border-white pointer-events-none shadow-[0_0_0_2px_rgba(11,13,20,0.8),0_0_14px_rgba(192,132,252,0.7)]"
        style={{ left: thumbX + 3, top: thumbY + 3, backgroundColor: thumbColor }}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel principal
// ---------------------------------------------------------------------------
export default function SolidColorControls({ onSetColor }) {
  const [hsv, setHsv] = useState(() => rgbToHsv(168, 85, 247));
  const [hexInput, setHexInput] = useState('#a855f7');
  const lastSentRef = useRef(0);
  const pendingRef = useRef(null);
  const timerRef = useRef(null);

  const rgb = hsvToRgb(hsv.h, hsv.s, hsv.v);
  const hex = toHex(rgb);
  const pureHue = toHex(hsvToRgb(hsv.h, hsv.s, 1));

  // Envío limitado (throttle) para no saturar el USB mientras se arrastra
  const flush = useCallback(() => {
    clearTimeout(timerRef.current);
    timerRef.current = null;
    if (pendingRef.current) {
      const [r, g, b] = pendingRef.current;
      pendingRef.current = null;
      lastSentRef.current = performance.now();
      onSetColor(r, g, b);
    }
  }, [onSetColor]);

  const sendThrottled = useCallback(
    (color) => {
      pendingRef.current = color;
      const elapsed = performance.now() - lastSentRef.current;
      if (elapsed >= SEND_INTERVAL_MS) flush();
      else if (!timerRef.current) timerRef.current = setTimeout(flush, SEND_INTERVAL_MS - elapsed);
    },
    [flush]
  );

  useEffect(() => () => clearTimeout(timerRef.current), []);

  const applyHsv = useCallback(
    (next) => {
      setHsv(next);
      const color = hsvToRgb(next.h, next.s, next.v);
      setHexInput(toHex(color));
      sendThrottled(color);
    },
    [sendThrottled]
  );

  const handleWheelChange = useCallback(
    ({ h, s }) => applyHsv({ h, s, v: hsv.v === 0 ? 1 : hsv.v }),
    [applyHsv, hsv.v]
  );

  const handleBrightness = (e) => applyHsv({ ...hsv, v: Number(e.target.value) / 100 });

  const handleHexChange = (e) => {
    const value = e.target.value;
    setHexInput(value);
    const parsed = parseHex(value);
    if (parsed) {
      setHsv(rgbToHsv(...parsed));
      sendThrottled(parsed);
    }
  };

  const handlePreset = (p) => {
    setHsv(rgbToHsv(...p.rgb));
    setHexInput(p.hex);
    pendingRef.current = p.rgb;
    flush();
  };

  return (
    <div className="bg-[#10131e]/90 border border-[#22273d] rounded-2xl p-5 flex flex-col gap-5 backdrop-blur-md shadow-lg">
      <div>
        <div className="text-base font-bold text-white flex items-center gap-2">
          <Palette className="w-5 h-5 text-purple-400" />
          Color Sólido Estático
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Ilumina todos los LEDs con un color uniforme de forma continua.
        </p>
      </div>

      {/* Rueda cromática + detalles */}
      <div className="flex flex-col md:flex-row items-center gap-7 bg-[#161a29] border border-[#22273d] p-5 rounded-xl">
        <ColorWheel hsv={hsv} onChange={handleWheelChange} onCommit={flush} />

        <div className="flex-1 w-full flex flex-col gap-5 min-w-0">
          {/* Vista previa */}
          <div className="flex items-center gap-4">
            <div
              className="w-16 h-16 rounded-2xl border-2 border-white/10 shrink-0 transition-colors duration-150"
              style={{ backgroundColor: hex, boxShadow: `0 0 24px ${hex}66` }}
            />
            <div className="min-w-0">
              <div className="text-sm font-bold text-white flex items-center gap-1.5">
                <Pipette className="w-3.5 h-3.5 text-purple-400" />
                Color Seleccionado
              </div>
              <div className="text-xs font-mono text-slate-400 mt-1">
                RGB({rgb[0]}, {rgb[1]}, {rgb[2]})
              </div>
            </div>
          </div>

          {/* HEX */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-slate-400">Código HEX</label>
            <input
              type="text"
              value={hexInput}
              onChange={handleHexChange}
              onBlur={() => setHexInput(hex)}
              maxLength={7}
              spellCheck={false}
              className="bg-[#10131e] border border-[#22273d] text-slate-100 rounded-lg px-3.5 py-2.5 text-sm font-mono uppercase outline-none focus:border-purple-400 transition-colors"
            />
          </div>

          {/* Brillo */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-medium text-slate-400 flex items-center gap-1.5">
                <Sun className="w-3.5 h-3.5 text-purple-400" />
                Intensidad del Color
              </span>
              <span className="text-purple-400 font-bold">{Math.round(hsv.v * 100)}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              value={Math.round(hsv.v * 100)}
              onChange={handleBrightness}
              onPointerUp={flush}
              style={{ background: `linear-gradient(to right, #000000, ${pureHue})` }}
            />
          </div>
        </div>
      </div>

      {/* Presets Grid */}
      <div>
        <label className="text-xs font-medium text-slate-400 block mb-3">
          Paleta de Colores Rápidos
        </label>
        <div className="flex flex-wrap gap-3">
          {PRESETS.map((p) => {
            const active = p.hex.toLowerCase() === hex.toLowerCase();
            return (
              <button
                key={p.name}
                style={{ backgroundColor: p.hex }}
                title={p.name}
                onClick={() => handlePreset(p)}
                className={`w-11 h-11 rounded-xl border-2 hover:scale-110 active:scale-95 shadow-md transition-all duration-150 cursor-pointer ${
                  active
                    ? 'border-purple-400 shadow-[0_0_14px_rgba(192,132,252,0.6)] scale-105'
                    : 'border-[#22273d] hover:border-white'
                }`}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
