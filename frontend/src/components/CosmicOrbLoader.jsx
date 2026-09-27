import React, { useEffect, useRef, useState } from "react";

/**
 * CosmicOrbLoader
 *
 * High-performance 3D Canvas Particle Orb loader.
 * Renders thousands of luminous starlight particles dynamically morphing
 * between fluid dynamic ribbons and a coherent celestial sphere with
 * additive glow blending, depth sorting, and specular starburst flares.
 */
export default function CosmicOrbLoader({ isReady = false, onFinish }) {
  const canvasRef = useRef(null);
  const [statusText, setStatusText] = useState("Initializing ProtoPilot...");
  const [fadingOut, setFadingOut] = useState(false);

  const mountTime = useRef(Date.now());

  // Status message sequence for cinematic feel
  useEffect(() => {
    const t1 = setTimeout(() => setStatusText("Loading neural workforce..."), 500);
    const t2 = setTimeout(() => setStatusText("Calibrating real-time audio..."), 1000);
    const t3 = setTimeout(() => setStatusText("Securing workspace session..."), 1500);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      clearTimeout(t3);
    };
  }, []);

  // When isReady is signaled, smoothly fade out after minimum cinematic duration
  useEffect(() => {
    if (isReady && !fadingOut) {
      const elapsed = Date.now() - mountTime.current;
      const delay = Math.max(0, 1600 - elapsed);
      const exitTimer = setTimeout(() => {
        setStatusText("Ready");
        setFadingOut(true);
        const finishTimer = setTimeout(() => {
          if (onFinish) onFinish();
        }, 500);
        return () => clearTimeout(finishTimer);
      }, delay);
      return () => clearTimeout(exitTimer);
    }
  }, [isReady, fadingOut, onFinish]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId;
    let width = (canvas.width = 460);
    let height = (canvas.height = 460);

    // Particle count: 1200 points for dense, radiant celestial structure
    const PARTICLE_COUNT = 1100;
    const particles = [];

    // Generate initial parametric coordinates
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Stratified spherical distribution + toroidal ribbon offsets
      const u = Math.random();
      const v = Math.random();
      const theta = u * 2 * Math.PI;
      const phi = Math.acos(2 * v - 1) - Math.PI / 2;

      // Random speed and sparkle properties
      particles.push({
        u,
        v,
        theta,
        phi,
        baseRadius: 130 + (Math.random() - 0.5) * 26,
        speed: 0.35 + Math.random() * 0.45,
        twinklePhase: Math.random() * Math.PI * 2,
        twinkleSpeed: 1.5 + Math.random() * 2.5,
        isFlare: Math.random() < 0.12, // 12% are sparkling star nodes
        // Color variance: ice cyan, electric blue, violet-blue, diamond white
        hue: 200 + Math.random() * 45, // 200 (cyan) to 245 (electric indigo)
        size: 0.8 + Math.random() * 1.6,
      });
    }

    let time = 0;
    let rotX = 0.2;
    let rotY = 0;
    let rotZ = 0.1;

    const render = () => {
      time += 0.016;
      rotY += 0.009;
      rotX += 0.004 * Math.sin(time * 0.5);
      rotZ += 0.003 * Math.cos(time * 0.4);

      ctx.clearRect(0, 0, width, height);

      const cx = width / 2;
      const cy = height / 2;
      const focalLength = 380;

      // Morph factor cycling between fluid wave ribbon and cohesive sphere
      // Gives the exact morphing ribbon-to-sphere transformation from user images
      const morph = 0.5 + 0.5 * Math.sin(time * 0.7);

      // We project and collect 3D coordinates for depth-sorting
      const renderList = [];

      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const p = particles[i];

        // 1. Sphere position
        const stheta = p.theta + time * p.speed * 0.2;
        const sphi = p.phi + Math.sin(time * 0.5 + p.theta) * 0.15;
        const sr = p.baseRadius * (1 + 0.12 * Math.sin(stheta * 4 + time * 1.5) * Math.cos(sphi * 3));

        const sx = sr * Math.cos(sphi) * Math.cos(stheta);
        const sy = sr * Math.sin(sphi);
        const sz = sr * Math.cos(sphi) * Math.sin(stheta);

        // 2. Flowing Ribbon / Manifold position (Images 1 & 2)
        // Multi-frequency wave folding in 3D
        const ru = p.u * Math.PI * 2 + time * p.speed * 0.4;
        const rv = (p.v - 0.5) * Math.PI;

        const ribbonR = 120 + 35 * Math.sin(ru * 3 + time * 1.8);
        const rx = ribbonR * Math.cos(ru) + 20 * Math.sin(rv * 2 + time);
        const ry = ribbonR * Math.sin(ru) * Math.cos(ru * 0.5) + 40 * Math.sin(rv * 3);
        const rz = 70 * Math.sin(ru * 2 + time * 1.2) + 45 * Math.cos(rv * 2);

        // Interpolate between Ribbon and Sphere
        const x0 = rx * (1 - morph) + sx * morph;
        const y0 = ry * (1 - morph) + sy * morph;
        const z0 = rz * (1 - morph) + sz * morph;

        // 3D Rotations
        // Rotate around Y
        const cosY = Math.cos(rotY);
        const sinY = Math.sin(rotY);
        const x1 = x0 * cosY - z0 * sinY;
        const z1 = x0 * sinY + z0 * cosY;

        // Rotate around X
        const cosX = Math.cos(rotX);
        const sinX = Math.sin(rotX);
        const y2 = y0 * cosX - z1 * sinX;
        const z2 = y0 * sinX + z1 * cosX;

        // Rotate around Z
        const cosZ = Math.cos(rotZ);
        const sinZ = Math.sin(rotZ);
        const x3 = x1 * cosZ - y2 * sinZ;
        const y3 = x1 * sinZ + y2 * cosZ;
        const z3 = z2;

        // Perspective Projection
        const scale = focalLength / (focalLength + z3);
        const projX = cx + x3 * scale;
        const projY = cy + y3 * scale;

        // Depth-based opacity & radius
        const depthAlpha = Math.max(0.1, Math.min(1.0, (z3 + 180) / 360));
        const twinkle = 0.75 + 0.25 * Math.sin(time * p.twinkleSpeed + p.twinklePhase);
        const finalAlpha = depthAlpha * twinkle;

        renderList.push({
          x: projX,
          y: projY,
          z: z3,
          scale,
          alpha: finalAlpha,
          size: p.size * scale,
          hue: p.hue,
          isFlare: p.isFlare && z3 > 20, // Only foreground particles sparkle
        });
      }

      // Sort back-to-front for proper depth stacking
      renderList.sort((a, b) => a.z - b.z);

      // Draw faint connections between nearby foreground points (neural filament web)
      ctx.globalCompositeOperation = "lighter";
      ctx.lineWidth = 0.5;

      // Draw particles with additive glowing light
      const len = renderList.length;
      for (let i = 0; i < len; i++) {
        const pt = renderList[i];
        if (pt.x < -20 || pt.x > width + 20 || pt.y < -20 || pt.y > height + 20) continue;

        ctx.fillStyle = `hsla(${pt.hue}, 95%, 72%, ${pt.alpha * 0.9})`;
        ctx.beginPath();
        ctx.arc(pt.x, pt.y, Math.max(0.6, pt.size), 0, Math.PI * 2);
        ctx.fill();

        // Extra white-hot core for bright front particles
        if (pt.z > 30) {
          ctx.fillStyle = `rgba(255, 255, 255, ${pt.alpha * 0.85})`;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, pt.size * 0.5, 0, Math.PI * 2);
          ctx.fill();
        }

        // Diamond starburst flare on highlight nodes
        if (pt.isFlare && pt.alpha > 0.6) {
          const flareLen = 4.5 * pt.scale;
          ctx.strokeStyle = `rgba(255, 255, 255, ${pt.alpha * 0.7})`;
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          // Horizontal lens glint
          ctx.moveTo(pt.x - flareLen, pt.y);
          ctx.lineTo(pt.x + flareLen, pt.y);
          // Vertical lens glint
          ctx.moveTo(pt.x, pt.y - flareLen);
          ctx.lineTo(pt.x, pt.y + flareLen);
          ctx.stroke();

          // Subtle diamond glow circle
          ctx.fillStyle = `rgba(186, 230, 253, ${pt.alpha * 0.35})`;
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, flareLen * 0.7, 0, Math.PI * 2);
          ctx.fill();
        }
      }

      animId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animId);
    };
  }, []);

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 99999,
        backgroundColor: "#05070e",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        userSelect: "none",
        overflow: "hidden",
        opacity: fadingOut ? 0 : 1,
        transform: fadingOut ? "scale(1.03)" : "scale(1)",
        transition: "opacity 0.45s cubic-bezier(0.16, 1, 0.3, 1), transform 0.45s cubic-bezier(0.16, 1, 0.3, 1)",
      }}
    >
      {/* Ambient background celestial gradient glow */}
      <div
        style={{
          position: "absolute",
          width: "560px",
          height: "560px",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(56, 189, 248, 0.16) 0%, rgba(99, 102, 241, 0.12) 35%, transparent 70%)",
          filter: "blur(60px)",
          pointerEvents: "none",
        }}
      />

      {/* 3D Cosmic Particle Canvas */}
      <div
        style={{
          position: "relative",
          width: "460px",
          height: "460px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <canvas
          ref={canvasRef}
          style={{
            width: "460px",
            height: "460px",
            display: "block",
            pointerEvents: "none",
          }}
        />
      </div>

      {/* Sleek App Branding & Dynamic Status */}
      <div
        style={{
          marginTop: "-15px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "14px",
          zIndex: 2,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "28px",
              height: "28px",
              borderRadius: "8px",
              background: "linear-gradient(135deg, #4F46E5, #06B6D4)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 16px rgba(79, 70, 229, 0.5)",
            }}
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#ffffff"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
            </svg>
          </div>
          <span
            style={{
              fontFamily: "'Space Grotesk', -apple-system, sans-serif",
              fontSize: "20px",
              fontWeight: "700",
              letterSpacing: "-0.03em",
              color: "#ffffff",
              textShadow: "0 2px 12px rgba(255, 255, 255, 0.15)",
            }}
          >
            ProtoPilot
          </span>
        </div>

        {/* Minimalist Progress Track */}
        <div
          style={{
            width: "160px",
            height: "2px",
            borderRadius: "999px",
            backgroundColor: "rgba(255, 255, 255, 0.08)",
            overflow: "hidden",
            position: "relative",
          }}
        >
          <div
            style={{
              position: "absolute",
              height: "100%",
              width: "50%",
              background: "linear-gradient(90deg, transparent, #38BDF8, #818CF8, transparent)",
              borderRadius: "999px",
              animation: "pp-cosmic-shimmer 1.4s ease-in-out infinite",
            }}
          />
        </div>

        {/* Animated Subtext */}
        <div
          style={{
            fontSize: "12.5px",
            fontWeight: "500",
            letterSpacing: "0.01em",
            color: "#94a3b8",
            height: "18px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all 0.3s ease",
          }}
        >
          {statusText}
        </div>
      </div>

      <style>{`
        @keyframes pp-cosmic-shimmer {
          0% { left: -50%; }
          100% { left: 150%; }
        }
      `}</style>
    </div>
  );
}
