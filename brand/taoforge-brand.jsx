import { useState } from "react";

const tabs = ["Identity", "Colors", "Typography", "Logo Suite", "Social Assets", "Guidelines"];

// --- LOGO SVG COMPONENTS ---

const ForgeIcon = ({ size = 48, color = "#FF3D2E", glow = false }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
    {glow && (
      <defs>
        <filter id="forge-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="3" />
        </filter>
        <radialGradient id="ember-grad" cx="50%" cy="60%" r="50%">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </radialGradient>
      </defs>
    )}
    {glow && <circle cx="32" cy="36" r="24" fill="url(#ember-grad)" />}
    {/* Anvil base */}
    <path d="M14 44 L18 38 L46 38 L50 44 L54 44 L54 48 L10 48 L10 44 Z" fill={color} />
    {/* Anvil horn */}
    <path d="M46 38 L56 34 L56 38 L46 38 Z" fill={color} opacity="0.8" />
    {/* Anvil body */}
    <rect x="16" y="32" width="32" height="6" rx="1" fill={color} />
    {/* Spark lines */}
    <line x1="28" y1="28" x2="24" y2="16" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
    <line x1="32" y1="28" x2="32" y2="14" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.9" />
    <line x1="36" y1="28" x2="40" y2="16" stroke={color} strokeWidth="1.5" strokeLinecap="round" opacity="0.7" />
    {/* Spark dots */}
    <circle cx="24" cy="15" r="1.5" fill={color} opacity="0.6" />
    <circle cx="32" cy="13" r="2" fill={color} />
    <circle cx="40" cy="15" r="1.5" fill={color} opacity="0.6" />
    {/* τ symbol embedded in anvil */}
    <text x="32" y="44" textAnchor="middle" fill="#0A0A0F" fontSize="10" fontWeight="700" fontFamily="'Courier New', monospace">τ</text>
  </svg>
);

const Wordmark = ({ size = "md", color = "#E8E8F0", accent = "#FF3D2E" }) => {
  const sizes = { sm: 18, md: 28, lg: 42, xl: 56 };
  const fs = sizes[size] || sizes.md;
  return (
    <div style={{ display: "flex", alignItems: "baseline", gap: fs * 0.05 }}>
      <span style={{
        fontFamily: "'Anybody', sans-serif",
        fontSize: fs,
        fontWeight: 800,
        color: accent,
        letterSpacing: -fs * 0.02,
        lineHeight: 1,
      }}>Tao</span>
      <span style={{
        fontFamily: "'Anybody', sans-serif",
        fontSize: fs,
        fontWeight: 800,
        color,
        letterSpacing: -fs * 0.02,
        lineHeight: 1,
      }}>Forge</span>
    </div>
  );
};

const Lockup = ({ variant = "horizontal", size = "md", theme = "dark" }) => {
  const isDark = theme === "dark";
  const color = isDark ? "#E8E8F0" : "#0A0A0F";
  const accent = "#FF3D2E";
  const iconSizes = { sm: 28, md: 40, lg: 56, xl: 72 };
  const iconSize = iconSizes[size] || 40;

  if (variant === "stacked") {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
        <ForgeIcon size={iconSize} color={accent} glow={isDark} />
        <Wordmark size={size} color={color} accent={accent} />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: iconSize * 0.3 }}>
      <ForgeIcon size={iconSize} color={accent} glow={isDark} />
      <Wordmark size={size} color={color} accent={accent} />
    </div>
  );
};

// --- BRAND TOKENS ---
const palette = {
  ember: { hex: "#FF3D2E", name: "Ember", role: "Primary accent — CTA, highlights, logo" },
  molten: { hex: "#FF6B35", name: "Molten", role: "Secondary warm — gradients, hover states" },
  heat: { hex: "#FFB800", name: "Heat", role: "Tertiary warm — notifications, badges" },
  forge: { hex: "#0A0A0F", name: "Forge Black", role: "Primary background" },
  anvil: { hex: "#12121A", name: "Anvil", role: "Card/surface background" },
  steel: { hex: "#1E1E2E", name: "Steel", role: "Borders, dividers" },
  smoke: { hex: "#8888A0", name: "Smoke", role: "Secondary text" },
  ash: { hex: "#555570", name: "Ash", role: "Muted text, captions" },
  white: { hex: "#E8E8F0", name: "White Hot", role: "Primary text" },
};

const ColorSwatch = ({ hex, name, role }) => {
  const [copied, setCopied] = useState(false);
  return (
    <div
      onClick={() => { navigator.clipboard?.writeText(hex); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
      style={{
        cursor: "pointer",
        background: "#12121A",
        border: "1px solid #1E1E2E",
        borderRadius: 10,
        overflow: "hidden",
        transition: "border-color 0.2s",
      }}
      onMouseEnter={e => e.currentTarget.style.borderColor = hex}
      onMouseLeave={e => e.currentTarget.style.borderColor = "#1E1E2E"}
    >
      <div style={{ height: 72, background: hex, position: "relative" }}>
        {copied && (
          <div style={{
            position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
            background: "rgba(0,0,0,0.6)", color: "#fff", fontSize: 11, fontFamily: "'DM Mono', monospace",
          }}>Copied</div>
        )}
      </div>
      <div style={{ padding: "10px 12px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#E8E8F0", fontSize: 13, fontWeight: 600 }}>{name}</span>
          <span style={{ color: "#555570", fontSize: 11, fontFamily: "'DM Mono', monospace" }}>{hex}</span>
        </div>
        <div style={{ color: "#8888A0", fontSize: 11, marginTop: 4 }}>{role}</div>
      </div>
    </div>
  );
};

// --- SOCIAL ASSET PREVIEWS ---

const TwitterBanner = () => (
  <div style={{
    width: "100%", aspectRatio: "3/1", background: "#0A0A0F", borderRadius: 10, overflow: "hidden",
    position: "relative", border: "1px solid #1E1E2E",
  }}>
    {/* Gradient heat wash */}
    <div style={{
      position: "absolute", bottom: 0, left: 0, right: 0, height: "60%",
      background: "linear-gradient(180deg, transparent 0%, rgba(255,61,46,0.08) 100%)",
    }} />
    {/* Grid lines */}
    <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.06 }}>
      {Array.from({ length: 20 }, (_, i) => (
        <line key={`v${i}`} x1={`${i * 5}%`} y1="0" x2={`${i * 5}%`} y2="100%" stroke="#FF3D2E" strokeWidth="0.5" />
      ))}
      {Array.from({ length: 8 }, (_, i) => (
        <line key={`h${i}`} x1="0" y1={`${i * 14}%`} x2="100%" y2={`${i * 14}%`} stroke="#FF3D2E" strokeWidth="0.5" />
      ))}
    </svg>
    <div style={{
      position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
      flexDirection: "column", gap: 12,
    }}>
      <Lockup variant="horizontal" size="lg" theme="dark" />
      <span style={{
        color: "#8888A0", fontSize: 12, fontFamily: "'DM Mono', monospace", letterSpacing: 4,
      }}>INTELLIGENCE FORGED ON TAO</span>
    </div>
    {/* Bittensor badge */}
    <div style={{
      position: "absolute", bottom: 16, right: 20,
      color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2,
    }}>BITTENSOR SUBNET</div>
  </div>
);

const OGCard = () => (
  <div style={{
    width: "100%", aspectRatio: "1.91/1", background: "#0A0A0F", borderRadius: 10, overflow: "hidden",
    position: "relative", border: "1px solid #1E1E2E",
  }}>
    {/* Corner accents */}
    <div style={{ position: "absolute", top: 0, left: 0, width: 60, height: 60 }}>
      <svg width="60" height="60"><line x1="0" y1="20" x2="20" y2="0" stroke="#FF3D2E" strokeWidth="1" opacity="0.4" /></svg>
    </div>
    <div style={{ position: "absolute", top: 0, right: 0, width: 60, height: 60, transform: "scaleX(-1)" }}>
      <svg width="60" height="60"><line x1="0" y1="20" x2="20" y2="0" stroke="#FF3D2E" strokeWidth="1" opacity="0.4" /></svg>
    </div>
    {/* Heat gradient */}
    <div style={{
      position: "absolute", bottom: 0, left: "20%", width: "60%", height: "50%",
      background: "radial-gradient(ellipse at bottom, rgba(255,61,46,0.12) 0%, transparent 70%)",
    }} />
    <div style={{
      position: "absolute", inset: 0, display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", gap: 16, padding: 32,
    }}>
      <ForgeIcon size={56} color="#FF3D2E" glow />
      <Wordmark size="xl" color="#E8E8F0" accent="#FF3D2E" />
      <div style={{
        color: "#8888A0", fontSize: 13, fontFamily: "'DM Mono', monospace",
        letterSpacing: 3, marginTop: 4,
      }}>RECURSIVE SELF-IMPROVEMENT REGISTRY</div>
      <div style={{
        color: "#555570", fontSize: 11, fontFamily: "'DM Mono', monospace",
        marginTop: 8, padding: "6px 16px", border: "1px solid #1E1E2E", borderRadius: 4,
      }}>BITTENSOR SUBNET</div>
    </div>
  </div>
);

const Avatar = () => (
  <div style={{
    width: 120, height: 120, borderRadius: "50%", background: "#0A0A0F",
    border: "2px solid #1E1E2E", display: "flex", alignItems: "center", justifyContent: "center",
    position: "relative", overflow: "hidden", flexShrink: 0,
  }}>
    <div style={{
      position: "absolute", bottom: "-20%", left: "10%", width: "80%", height: "60%",
      background: "radial-gradient(ellipse at bottom, rgba(255,61,46,0.2) 0%, transparent 70%)",
    }} />
    <ForgeIcon size={60} color="#FF3D2E" glow />
  </div>
);

// --- MAIN COMPONENT ---
export default function TaoForgeBrand() {
  const [tab, setTab] = useState("Identity");

  return (
    <div style={{ background: "#0A0A0F", color: "#E8E8F0", minHeight: "100vh", fontFamily: "'Instrument Sans', -apple-system, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Anybody:wght@400;600;700;800&family=DM+Mono:wght@400;500&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{
        padding: "32px 32px 24px", borderBottom: "1px solid #1E1E2E",
        background: "linear-gradient(180deg, rgba(255,61,46,0.06) 0%, #0A0A0F 100%)",
      }}>
        <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 4, marginBottom: 12 }}>
          BRAND SYSTEM v1.0
        </div>
        <Lockup variant="horizontal" size="lg" theme="dark" />
        <p style={{ color: "#8888A0", fontSize: 14, margin: "12px 0 0", maxWidth: 480 }}>
          Brand identity system for TaoForge — the recursive self-improvement registry on Bittensor.
        </p>
      </div>

      {/* Tab nav */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #1E1E2E", overflowX: "auto", position: "sticky", top: 0, zIndex: 10, background: "#0A0A0F" }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            background: tab === t ? "rgba(255,61,46,0.1)" : "transparent",
            border: "none", borderBottom: tab === t ? "2px solid #FF3D2E" : "2px solid transparent",
            color: tab === t ? "#FF3D2E" : "#8888A0",
            padding: "12px 20px", fontSize: 12, fontWeight: 600,
            fontFamily: "'DM Mono', monospace", letterSpacing: 1,
            cursor: "pointer", whiteSpace: "nowrap", transition: "all 0.2s",
          }}>{t}</button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "32px 24px" }}>

        {/* --- IDENTITY --- */}
        {tab === "Identity" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Brand Concept</h2>
            <p style={{ color: "#8888A0", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              TaoForge evokes the act of forging — raw intelligence shaped and hardened through recursive pressure. The brand is industrial but precise, dark but warm where it matters. Every asset should feel like it was hammered into existence, not generated.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 32 }}>
              {[
                { label: "Voice", value: "Direct, technical, zero fluff. Speaks to builders." },
                { label: "Aesthetic", value: "Industrial minimal — dark forge, ember accents, precise grids." },
                { label: "Tagline", value: "Intelligence forged on TAO" },
                { label: "Audience", value: "Bittensor builders, AI researchers, agent developers" },
              ].map((item, i) => (
                <div key={i} style={{ background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 8, padding: "16px 20px" }}>
                  <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 6 }}>{item.label.toUpperCase()}</div>
                  <div style={{ color: "#E8E8F0", fontSize: 13, fontWeight: 500, lineHeight: 1.5 }}>{item.value}</div>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>Primary Lockup</h3>
            <div style={{
              background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 12, padding: 40,
              display: "flex", flexDirection: "column", alignItems: "center", gap: 32,
            }}>
              <Lockup variant="horizontal" size="xl" theme="dark" />
              <div style={{ width: "100%", height: 1, background: "#1E1E2E" }} />
              <Lockup variant="stacked" size="lg" theme="dark" />
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 32, marginBottom: 16 }}>Icon & Avatar</h3>
            <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
              <Avatar />
              <div style={{
                width: 120, height: 120, borderRadius: 16, background: "#0A0A0F",
                border: "2px solid #1E1E2E", display: "flex", alignItems: "center", justifyContent: "center",
                position: "relative", overflow: "hidden",
              }}>
                <div style={{
                  position: "absolute", bottom: "-20%", left: "10%", width: "80%", height: "60%",
                  background: "radial-gradient(ellipse at bottom, rgba(255,61,46,0.2) 0%, transparent 70%)",
                }} />
                <ForgeIcon size={60} color="#FF3D2E" glow />
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ color: "#8888A0", fontSize: 12 }}>Circle — socials / pfp</div>
                <div style={{ color: "#8888A0", fontSize: 12 }}>Rounded square — app icon</div>
                <div style={{ color: "#555570", fontSize: 11, fontFamily: "'DM Mono', monospace", marginTop: 4 }}>Min size: 32×32px</div>
              </div>
            </div>
          </div>
        )}

        {/* --- COLORS --- */}
        {tab === "Colors" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Color System</h2>
            <p style={{ color: "#8888A0", fontSize: 14, lineHeight: 1.7, marginBottom: 24 }}>
              Built on a forge metaphor — dark backgrounds with ember and heat accents. Click any swatch to copy its hex value.
            </p>

            <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 12 }}>ACCENT PALETTE</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 28 }}>
              <ColorSwatch {...palette.ember} />
              <ColorSwatch {...palette.molten} />
              <ColorSwatch {...palette.heat} />
            </div>

            <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 12 }}>NEUTRAL PALETTE</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 28 }}>
              <ColorSwatch {...palette.forge} />
              <ColorSwatch {...palette.anvil} />
              <ColorSwatch {...palette.steel} />
            </div>

            <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 12 }}>TEXT PALETTE</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 28 }}>
              <ColorSwatch {...palette.white} />
              <ColorSwatch {...palette.smoke} />
              <ColorSwatch {...palette.ash} />
            </div>

            <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 12 }}>GRADIENT</div>
            <div style={{
              height: 80, borderRadius: 10,
              background: "linear-gradient(135deg, #FF3D2E 0%, #FF6B35 50%, #FFB800 100%)",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              <span style={{ color: "#0A0A0F", fontFamily: "'DM Mono', monospace", fontSize: 12, fontWeight: 600, letterSpacing: 2 }}>
                EMBER → MOLTEN → HEAT
              </span>
            </div>
          </div>
        )}

        {/* --- TYPOGRAPHY --- */}
        {tab === "Typography" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Type System</h2>
            <p style={{ color: "#8888A0", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              Two typefaces. Anybody for display — heavy, industrial, with character. DM Mono for technical content — clean monospace with excellent readability.
            </p>

            <div style={{ background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 12, padding: "32px 28px", marginBottom: 16 }}>
              <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 20 }}>DISPLAY — ANYBODY 800</div>
              {[
                { size: 48, text: "TaoForge", tracking: -1.5 },
                { size: 32, text: "Intelligence Forged on TAO", tracking: -0.5 },
                { size: 24, text: "Recursive Self-Improvement", tracking: -0.3 },
              ].map((s, i) => (
                <div key={i} style={{
                  fontFamily: "'Anybody', sans-serif", fontSize: s.size, fontWeight: 800,
                  color: "#E8E8F0", letterSpacing: s.tracking, lineHeight: 1.2, marginBottom: 16,
                }}>{s.text}</div>
              ))}
            </div>

            <div style={{ background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 12, padding: "32px 28px", marginBottom: 16 }}>
              <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 20 }}>MONO — DM MONO 400 / 500</div>
              {[
                { size: 16, text: "proof_of_improvement.verify()", weight: 500 },
                { size: 14, text: "agent.propose_mutation(delta, bond=2.5)", weight: 400 },
                { size: 12, text: "// Verified improvement: +3.4% on bench_v3.2", weight: 400 },
              ].map((s, i) => (
                <div key={i} style={{
                  fontFamily: "'DM Mono', monospace", fontSize: s.size, fontWeight: s.weight,
                  color: i === 0 ? "#FF3D2E" : "#8888A0", lineHeight: 1.6, marginBottom: 12,
                }}>{s.text}</div>
              ))}
            </div>

            <div style={{ background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 12, padding: "32px 28px" }}>
              <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 20 }}>BODY — INSTRUMENT SANS 400 / 600</div>
              <div style={{ fontFamily: "'Instrument Sans', sans-serif", fontSize: 16, color: "#E8E8F0", fontWeight: 600, marginBottom: 8 }}>
                A subnet where agents compete to improve themselves.
              </div>
              <div style={{ fontFamily: "'Instrument Sans', sans-serif", fontSize: 14, color: "#8888A0", lineHeight: 1.7 }}>
                TaoForge creates an economic game where autonomous agents propose mutations to themselves, validators verify the improvements are real, and the evolutionary trajectory becomes a public, verifiable record on the Bittensor network.
              </div>
            </div>
          </div>
        )}

        {/* --- LOGO SUITE --- */}
        {tab === "Logo Suite" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Logo Variations</h2>
            <p style={{ color: "#8888A0", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              All lockup variants across dark and light contexts.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
              {/* Dark horizontal */}
              <div style={{ background: "#0A0A0F", border: "1px solid #1E1E2E", borderRadius: 12, padding: 32, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2 }}>DARK — HORIZONTAL</div>
                <Lockup variant="horizontal" size="md" theme="dark" />
              </div>
              {/* Light horizontal */}
              <div style={{ background: "#F0F0F0", border: "1px solid #ddd", borderRadius: 12, padding: 32, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <div style={{ color: "#999", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2 }}>LIGHT — HORIZONTAL</div>
                <Lockup variant="horizontal" size="md" theme="light" />
              </div>
              {/* Dark stacked */}
              <div style={{ background: "#0A0A0F", border: "1px solid #1E1E2E", borderRadius: 12, padding: 32, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2 }}>DARK — STACKED</div>
                <Lockup variant="stacked" size="md" theme="dark" />
              </div>
              {/* Light stacked */}
              <div style={{ background: "#F0F0F0", border: "1px solid #ddd", borderRadius: 12, padding: 32, display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                <div style={{ color: "#999", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2 }}>LIGHT — STACKED</div>
                <Lockup variant="stacked" size="md" theme="light" />
              </div>
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 32, marginBottom: 16 }}>Icon Only</h3>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {[64, 48, 32, 24].map(s => (
                <div key={s} style={{
                  background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 8,
                  width: 96, height: 96, display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center", gap: 8,
                }}>
                  <ForgeIcon size={s} color="#FF3D2E" glow />
                  <span style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace" }}>{s}px</span>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 32, marginBottom: 16 }}>Wordmark Only</h3>
            <div style={{ background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 12, padding: "24px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
              <Wordmark size="xl" />
              <Wordmark size="lg" />
              <Wordmark size="md" />
              <Wordmark size="sm" />
            </div>
          </div>
        )}

        {/* --- SOCIAL ASSETS --- */}
        {tab === "Social Assets" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Social & Marketing Assets</h2>
            <p style={{ color: "#8888A0", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              Ready-to-use templates for X/Twitter, Discord, and link previews.
            </p>

            <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 12 }}>
              X / TWITTER BANNER — 1500×500
            </div>
            <TwitterBanner />

            <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 12, marginTop: 32 }}>
              OG CARD — 1200×630
            </div>
            <OGCard />

            <div style={{ color: "#555570", fontSize: 10, fontFamily: "'DM Mono', monospace", letterSpacing: 2, marginBottom: 12, marginTop: 32 }}>
              PROFILE PICTURE
            </div>
            <div style={{ display: "flex", gap: 20, alignItems: "end" }}>
              <Avatar />
              <div style={{
                width: 72, height: 72, borderRadius: "50%", background: "#0A0A0F",
                border: "2px solid #1E1E2E", display: "flex", alignItems: "center", justifyContent: "center",
                position: "relative", overflow: "hidden",
              }}>
                <div style={{
                  position: "absolute", bottom: "-20%", left: "10%", width: "80%", height: "60%",
                  background: "radial-gradient(ellipse at bottom, rgba(255,61,46,0.15) 0%, transparent 70%)",
                }} />
                <ForgeIcon size={36} color="#FF3D2E" glow />
              </div>
              <div style={{
                width: 44, height: 44, borderRadius: "50%", background: "#0A0A0F",
                border: "1.5px solid #1E1E2E", display: "flex", alignItems: "center", justifyContent: "center",
                position: "relative", overflow: "hidden",
              }}>
                <ForgeIcon size={24} color="#FF3D2E" />
              </div>
            </div>
          </div>
        )}

        {/* --- GUIDELINES --- */}
        {tab === "Guidelines" && (
          <div>
            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>Usage Guidelines</h2>
            <p style={{ color: "#8888A0", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              Rules for maintaining brand consistency across all touchpoints.
            </p>

            {[
              {
                title: "DO",
                accent: "#00FF88",
                items: [
                  "Use the ember accent (#FF3D2E) as the primary brand color",
                  "Maintain minimum clear space equal to the icon height around the lockup",
                  "Use Forge Black (#0A0A0F) as the primary background — dark mode is default",
                  "Pair Anybody (display) with DM Mono (technical) and Instrument Sans (body)",
                  "Use the gradient (Ember → Molten → Heat) sparingly for emphasis",
                  "Always capitalize as 'TaoForge' — one word, capital T and F",
                ],
              },
              {
                title: "DON'T",
                accent: "#FF3D2E",
                items: [
                  "Don't place the logo on busy or low-contrast backgrounds",
                  "Don't rotate, stretch, or distort the logo or icon",
                  "Don't use the ember gradient as a background fill — it's for accents only",
                  "Don't separate 'Tao' and 'Forge' with a space — it's one word",
                  "Don't swap the Tao/Forge color split (Tao is always ember, Forge is always the text color)",
                  "Don't use light mode as the default context — dark is primary",
                ],
              },
            ].map((section, i) => (
              <div key={i} style={{
                background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 12,
                padding: "24px 28px", marginBottom: 16, borderLeft: `3px solid ${section.accent}`,
              }}>
                <div style={{ color: section.accent, fontSize: 11, fontWeight: 700, letterSpacing: 2, fontFamily: "'DM Mono', monospace", marginBottom: 14 }}>
                  {section.title}
                </div>
                {section.items.map((item, j) => (
                  <div key={j} style={{ color: "#8888A0", fontSize: 13, lineHeight: 1.6, marginBottom: 6, paddingLeft: 12, borderLeft: "1px solid #1E1E2E" }}>
                    {item}
                  </div>
                ))}
              </div>
            ))}

            <div style={{
              background: "#12121A", border: "1px solid #1E1E2E", borderRadius: 12,
              padding: "24px 28px", marginTop: 24,
            }}>
              <div style={{ color: "#FFB800", fontSize: 11, fontWeight: 700, letterSpacing: 2, fontFamily: "'DM Mono', monospace", marginBottom: 14 }}>
                FILE NAMING CONVENTION
              </div>
              <pre style={{
                color: "#8888A0", fontFamily: "'DM Mono', monospace", fontSize: 12, lineHeight: 1.8, margin: 0,
              }}>
{`taoforge-logo-horizontal-dark.svg
taoforge-logo-horizontal-light.svg
taoforge-logo-stacked-dark.svg
taoforge-logo-stacked-light.svg
taoforge-icon-64.svg
taoforge-icon-32.svg
taoforge-banner-x-1500x500.png
taoforge-og-1200x630.png
taoforge-avatar-400x400.png`}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
