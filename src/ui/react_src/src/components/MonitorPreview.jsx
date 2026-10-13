import React, { useMemo } from 'react';

/**
 * MonitorPreview - Visual monitor representation for the modular 3-strip system.
 * Left (17 LEDs / 9 zones) + Top (29 LEDs / 16 zones) + Right (17 LEDs / 9 zones) = 63 LEDs / 34 zones.
 */
export default function MonitorPreview({ mode, resolution, ledColors, isRunning, monitorName }) {
  const W = 460;
  const H = 258;

  // Compute 34 LED positions across the 3 modular edges: Left (9), Top (16), Right (9)
  const dots = useMemo(() => {
    const coords = [];

    // 1. Left module (bottom to top: 9 zones)
    for (let i = 0; i < 9; i++) {
      const y = H - ((i + 0.5) * (H / 9));
      coords.push({ x: 0, y, id: i + 1, module: 'Izquierda (17 LEDs)' });
    }

    // 2. Top module (left to right: 16 zones)
    for (let i = 0; i < 16; i++) {
      const x = (i + 0.5) * (W / 16);
      coords.push({ x, y: 0, id: 9 + i + 1, module: 'Superior (29 LEDs)' });
    }

    // 3. Right module (top to bottom: 9 zones)
    for (let i = 0; i < 9; i++) {
      const y = (i + 0.5) * (H / 9);
      coords.push({ x: W, y, id: 25 + i + 1, module: 'Derecha (17 LEDs)' });
    }

    return coords;
  }, []);

  const modeLabel = useMemo(() => {
    if (mode === 'ambilight' && isRunning) return 'Ambilight Transmitiendo';
    if (mode === 'solid') return 'Color Sólido Activo';
    if (mode === 'effect') return 'Efecto de Hardware Activo';
    return 'En Reposo';
  }, [mode, isRunning]);

  return (
    <div className="bg-[#10131e]/90 border border-[#22273d] rounded-2xl p-6 flex flex-col items-center relative shadow-xl backdrop-blur-md">
      {/* Monitor Outer Frame */}
      <div className="w-[460px] h-[258px] bg-[#06070a] border-4 border-[#202538] rounded-lg relative flex items-center justify-center shadow-2xl">
        {/* 34 Perimeter LED nodes across Left (9), Top (16), Right (9) */}
        {dots.map((dot, idx) => {
          const rgb = ledColors && ledColors[idx] ? ledColors[idx] : [28, 33, 53];
          const hasColor = isRunning || (mode === 'solid' && ledColors);
          const bg = hasColor ? `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})` : '#1c2135';
          const shadow = hasColor ? `0 0 10px rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 0.85)` : 'none';

          return (
            <div
              key={idx}
              className="absolute w-2.5 h-2.5 rounded-full -translate-x-1/2 -translate-y-1/2 transition-all duration-100 ease-linear pointer-events-none"
              style={{
                left: `${dot.x}px`,
                top: `${dot.y}px`,
                backgroundColor: bg,
                boxShadow: shadow,
              }}
              title={`Zona #${idx + 1} &bull; ${dot.module}`}
            />
          );
        })}

        {/* Center Virtual Screen Content */}
        <div className="flex flex-col items-center gap-1.5 text-center select-none">
          <div className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
            {isRunning && <span className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />}
            {modeLabel}
          </div>
          <div className="text-xs text-slate-400 font-medium">
            {monitorName || 'DISPLAY1'} &bull; {resolution || '1920x1080'}
          </div>
          <div className="text-[10px] text-purple-400/90 font-mono bg-purple-500/10 px-2 py-0.5 rounded-full border border-purple-500/20 mt-0.5">
            17 LEDs Izq &bull; 29 LEDs Arriba &bull; 17 LEDs Der
          </div>
        </div>
      </div>

      {/* Monitor Stand & Base */}
      <div className="w-20 h-4 bg-[#181c2c] rounded-b-md" />
      <div className="w-36 h-1.5 bg-[#232840] rounded-full shadow-md" />
    </div>
  );
}
