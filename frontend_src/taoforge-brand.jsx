import { useState } from "react";

const tabs = ["Identity", "Colors", "Typography", "Logo Suite", "Social Assets", "Guidelines"];

// --- LOGO SVG COMPONENTS ---

const ForgeIcon = ({ size = 48, ember = "#E63B2E", dark = false }) => {
  const metal = dark ? "#FFFFFF" : "#000000";
  const tauColor = dark ? "#000000" : "#FFFFFF";
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      {/* Anvil base */}
      <path d="M14 44 L18 38 L46 38 L50 44 L54 44 L54 48 L10 48 L10 44 Z" fill={metal} />
      {/* Anvil horn */}
      <path d="M46 38 L56 34 L56 38 L46 38 Z" fill={metal} opacity="0.65" />
      {/* Anvil body */}
      <rect x="16" y="32" width="32" height="6" rx="1" fill={metal} />
      {/* Spark lines — EMBER RED */}
      <line x1="28" y1="28" x2="24" y2="16" stroke={ember} strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
      <line x1="32" y1="28" x2="32" y2="14" stroke={ember} strokeWidth="1.5" strokeLinecap="round" opacity="0.9" />
      <line x1="36" y1="28" x2="40" y2="16" stroke={ember} strokeWidth="1.5" strokeLinecap="round" opacity="0.6" />
      {/* Spark dots — EMBER RED */}
      <circle cx="24" cy="15" r="1.5" fill={ember} opacity="0.55" />
      <circle cx="32" cy="13" r="2" fill={ember} />
      <circle cx="40" cy="15" r="1.5" fill={ember} opacity="0.55" />
      {/* τ symbol embedded in anvil */}
      <text x="32" y="45" textAnchor="middle" fill={tauColor} fontSize="10" fontWeight="700" fontFamily="'Courier New', monospace">τ</text>
    </svg>
  );
};

const Wordmark = ({ size = "md", dark = false }) => {
  const sizes = { sm: 18, md: 28, lg: 42, xl: 56 };
  const fs = sizes[size] || sizes.md;
  const color = dark ? "#FFFFFF" : "#000000";
  return (
    <span style={{
      fontFamily: "'Manrope', sans-serif",
      fontSize: fs,
      fontWeight: 700,
      color,
      letterSpacing: -fs * 0.015,
      lineHeight: 1,
    }}>τaoForge</span>
  );
};

const Lockup = ({ variant = "horizontal", size = "md", dark = false, ember = "#E63B2E" }) => {
  const iconSizes = { sm: 28, md: 40, lg: 56, xl: 72 };
  const iconSize = iconSizes[size] || 40;

  if (variant === "stacked") {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
        <ForgeIcon size={iconSize} ember={ember} dark={dark} />
        <Wordmark size={size} dark={dark} />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: iconSize * 0.3 }}>
      <ForgeIcon size={iconSize} ember={ember} dark={dark} />
      <Wordmark size={size} dark={dark} />
    </div>
  );
};

// --- BRAND TOKENS ---
const palette = {
  ember: { hex: "#E63B2E", name: "Ember", role: "Sparks only — icon accent, CTA highlights" },
  emberLight: { hex: "#F4D0CC", name: "Ember Light", role: "Hover states, subtle backgrounds" },
  black: { hex: "#000000", name: "Black", role: "Primary text, headings" },
  dark: { hex: "#1A1A1A", name: "Dark", role: "Secondary text, body copy" },
  mid: { hex: "#666666", name: "Mid", role: "Captions, muted text" },
  light: { hex: "#999999", name: "Light", role: "Placeholders, disabled states" },
  border: { hex: "#E0E0E0", name: "Border", role: "Dividers, card borders" },
  surface: { hex: "#F5F5F5", name: "Surface", role: "Card backgrounds, sections" },
  white: { hex: "#FFFFFF", name: "White", role: "Primary background" },
};

const ColorSwatch = ({ hex, name, role }) => {
  const [copied, setCopied] = useState(false);
  const isLight = ["#FFFFFF", "#F5F5F5", "#E0E0E0", "#F4D0CC"].includes(hex);
  return (
    <div
      onClick={() => { navigator.clipboard?.writeText(hex); setCopied(true); setTimeout(() => setCopied(false), 1200); }}
      style={{
        cursor: "pointer",
        background: "#fff",
        border: "1px solid #E0E0E0",
        borderRadius: 8,
        overflow: "hidden",
        transition: "box-shadow 0.2s",
      }}
      onMouseEnter={e => e.currentTarget.style.boxShadow = "0 2px 12px rgba(0,0,0,0.08)"}
      onMouseLeave={e => e.currentTarget.style.boxShadow = "none"}
    >
      <div style={{ height: 64, background: hex, position: "relative", borderBottom: isLight ? "1px solid #E0E0E0" : "none" }}>
        {copied && (
          <div style={{
            position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
            background: "rgba(0,0,0,0.5)", color: "#fff", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace",
          }}>Copied</div>
        )}
      </div>
      <div style={{ padding: "10px 12px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ color: "#000", fontSize: 13, fontWeight: 600 }}>{name}</span>
          <span style={{ color: "#999", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace" }}>{hex}</span>
        </div>
        <div style={{ color: "#666", fontSize: 11, marginTop: 4 }}>{role}</div>
      </div>
    </div>
  );
};

// --- SOCIAL ASSET PREVIEWS ---

const TwitterBanner = () => (
  <div style={{
    width: "100%", aspectRatio: "3/1", background: "#FFFFFF", borderRadius: 8, overflow: "hidden",
    position: "relative", border: "1px solid #E0E0E0",
  }}>
    <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.04 }}>
      {Array.from({ length: 30 }, (_, i) => (
        <line key={`v${i}`} x1={`${i * 3.33}%`} y1="0" x2={`${i * 3.33}%`} y2="100%" stroke="#000" strokeWidth="0.5" />
      ))}
      {Array.from({ length: 10 }, (_, i) => (
        <line key={`h${i}`} x1="0" y1={`${i * 10}%`} x2="100%" y2={`${i * 10}%`} stroke="#000" strokeWidth="0.5" />
      ))}
    </svg>
    <div style={{
      position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
      flexDirection: "column", gap: 10,
    }}>
      <Lockup variant="horizontal" size="lg" dark={false} />
      <span style={{ color: "#999", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 4, textTransform: "uppercase" }}>
        Intelligence forged on TAO
      </span>
    </div>
    <div style={{
      position: "absolute", bottom: 14, right: 18,
      color: "#CCC", fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 3, textTransform: "uppercase",
    }}>Built on Bittensor</div>
  </div>
);

const TwitterBannerDark = () => (
  <div style={{
    width: "100%", aspectRatio: "3/1", background: "#000", borderRadius: 8, overflow: "hidden",
    position: "relative", border: "1px solid #222",
  }}>
    <svg style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.06 }}>
      {Array.from({ length: 30 }, (_, i) => (
        <line key={`v${i}`} x1={`${i * 3.33}%`} y1="0" x2={`${i * 3.33}%`} y2="100%" stroke="#fff" strokeWidth="0.5" />
      ))}
      {Array.from({ length: 10 }, (_, i) => (
        <line key={`h${i}`} x1="0" y1={`${i * 10}%`} x2="100%" y2={`${i * 10}%`} stroke="#fff" strokeWidth="0.5" />
      ))}
    </svg>
    <div style={{
      position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
      flexDirection: "column", gap: 10,
    }}>
      <Lockup variant="horizontal" size="lg" dark={true} />
      <span style={{ color: "#555", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 4, textTransform: "uppercase" }}>
        Intelligence forged on TAO
      </span>
    </div>
    <div style={{
      position: "absolute", bottom: 14, right: 18,
      color: "#333", fontSize: 9, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 3, textTransform: "uppercase",
    }}>Built on Bittensor</div>
  </div>
);

const OGCard = ({ dark = false }) => {
  const bg = dark ? "#000" : "#FFFFFF";
  const text = dark ? "#FFF" : "#000";
  const muted = dark ? "#555" : "#999";
  const border = dark ? "#222" : "#E0E0E0";
  return (
    <div style={{
      width: "100%", aspectRatio: "1.91/1", background: bg, borderRadius: 8, overflow: "hidden",
      position: "relative", border: `1px solid ${border}`,
    }}>
      <div style={{
        position: "absolute", inset: 0, display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: 14, padding: 32,
      }}>
        <ForgeIcon size={52} ember="#E63B2E" dark={dark} />
        <span style={{
          fontFamily: "'Manrope', sans-serif", fontSize: 44, fontWeight: 700,
          color: text, letterSpacing: -0.5,
        }}>τaoForge</span>
        <div style={{
          color: muted, fontSize: 12, fontFamily: "'IBM Plex Mono', monospace",
          letterSpacing: 4, textTransform: "uppercase",
        }}>Recursive Self-Improvement Registry</div>
        <div style={{
          color: muted, fontSize: 10, fontFamily: "'IBM Plex Mono', monospace",
          marginTop: 8, padding: "5px 14px", border: `1px solid ${border}`, borderRadius: 3,
          letterSpacing: 2, textTransform: "uppercase",
        }}>Built on Bittensor</div>
      </div>
    </div>
  );
};

const AvatarCircle = ({ size = 120, dark = false }) => (
  <div style={{
    width: size, height: size, borderRadius: "50%", background: dark ? "#000" : "#fff",
    border: `1.5px solid ${dark ? "#222" : "#E0E0E0"}`, display: "flex", alignItems: "center", justifyContent: "center",
    flexShrink: 0,
  }}>
    <ForgeIcon size={size * 0.5} ember="#E63B2E" dark={dark} />
  </div>
);

// --- MAIN COMPONENT ---
export default function TaoForgeBrand() {
  const [tab, setTab] = useState("Identity");

  return (
    <div style={{ background: "#FFFFFF", color: "#000", minHeight: "100vh", fontFamily: "'Instrument Sans', -apple-system, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600&family=Instrument+Sans:wght@400;500;600;700&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ padding: "36px 36px 28px", borderBottom: "1px solid #E0E0E0" }}>
        <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 4, marginBottom: 16, textTransform: "uppercase" }}>
          Brand System v1.0
        </div>
        <Lockup variant="horizontal" size="lg" dark={false} />
        <p style={{ color: "#666", fontSize: 14, margin: "14px 0 0", maxWidth: 500, lineHeight: 1.6 }}>
          Brand identity system for τaoForge — the recursive self-improvement registry on Bittensor.
        </p>
      </div>

      {/* Tab nav */}
      <div style={{ display: "flex", gap: 0, borderBottom: "1px solid #E0E0E0", overflowX: "auto", position: "sticky", top: 0, zIndex: 10, background: "#fff" }}>
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            background: "transparent",
            border: "none", borderBottom: tab === t ? "2px solid #000" : "2px solid transparent",
            color: tab === t ? "#000" : "#999",
            padding: "13px 22px", fontSize: 12, fontWeight: 600,
            fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 1,
            cursor: "pointer", whiteSpace: "nowrap", transition: "all 0.15s",
            textTransform: "uppercase",
          }}>{t}</button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 860, margin: "0 auto", padding: "36px 24px" }}>

        {tab === "Identity" && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, letterSpacing: -0.3 }}>Brand Concept</h2>
            <p style={{ color: "#666", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              τaoForge follows Bittensor's stark, reduced visual language — white space, black type, no ornamentation. The only color in the system is Ember red, reserved for the sparks rising from the anvil icon. The anvil itself is black or white depending on context. The brand communicates through restraint and precision — the red sparks are the one mark of transformation in an otherwise monochrome system.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 36 }}>
              {[
                { label: "Voice", value: "Direct, technical, zero fluff. Speaks to builders." },
                { label: "Aesthetic", value: "Stark white, black type, black anvil with red sparks. Bittensor-native." },
                { label: "Tagline", value: "Intelligence forged on TAO" },
                { label: "Audience", value: "Bittensor builders, AI researchers, agent developers" },
              ].map((item, i) => (
                <div key={i} style={{ background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 6, padding: "16px 20px" }}>
                  <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 6, textTransform: "uppercase" }}>{item.label}</div>
                  <div style={{ color: "#000", fontSize: 13, fontWeight: 500, lineHeight: 1.5 }}>{item.value}</div>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, letterSpacing: -0.2 }}>Primary Lockup — Light</h3>
            <div style={{
              background: "#fff", border: "1px solid #E0E0E0", borderRadius: 8, padding: 48,
              display: "flex", flexDirection: "column", alignItems: "center", gap: 36,
            }}>
              <Lockup variant="horizontal" size="xl" dark={false} />
              <div style={{ width: "100%", height: 1, background: "#E0E0E0" }} />
              <Lockup variant="stacked" size="lg" dark={false} />
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 36, marginBottom: 16, letterSpacing: -0.2 }}>Primary Lockup — Dark</h3>
            <div style={{
              background: "#000", border: "1px solid #222", borderRadius: 8, padding: 48,
              display: "flex", flexDirection: "column", alignItems: "center", gap: 36,
            }}>
              <Lockup variant="horizontal" size="xl" dark={true} />
              <div style={{ width: "100%", height: 1, background: "#222" }} />
              <Lockup variant="stacked" size="lg" dark={true} />
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 36, marginBottom: 16, letterSpacing: -0.2 }}>Icon & Avatar</h3>
            <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
              <AvatarCircle size={100} />
              <AvatarCircle size={100} dark />
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                <div style={{ color: "#666", fontSize: 12 }}>Light — socials, docs, web</div>
                <div style={{ color: "#666", fontSize: 12 }}>Dark — Discord, terminal contexts</div>
                <div style={{ color: "#999", fontSize: 11, fontFamily: "'IBM Plex Mono', monospace", marginTop: 4 }}>Min size: 32×32px</div>
              </div>
            </div>
          </div>
        )}

        {tab === "Colors" && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, letterSpacing: -0.3 }}>Color System</h2>
            <p style={{ color: "#666", fontSize: 14, lineHeight: 1.7, marginBottom: 28 }}>
              Monochrome foundation with a single accent. Ember red is reserved for the forge icon and critical interactive elements. Everything else is black, white, and grey. Click any swatch to copy.
            </p>

            <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 12, textTransform: "uppercase" }}>Accent</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 28 }}>
              <ColorSwatch {...palette.ember} />
              <ColorSwatch {...palette.emberLight} />
            </div>

            <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 12, textTransform: "uppercase" }}>Neutrals</div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 12 }}>
              <ColorSwatch {...palette.black} />
              <ColorSwatch {...palette.dark} />
              <ColorSwatch {...palette.mid} />
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 28 }}>
              <ColorSwatch {...palette.light} />
              <ColorSwatch {...palette.border} />
              <ColorSwatch {...palette.surface} />
            </div>

            <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 12, textTransform: "uppercase" }}>Background</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <ColorSwatch {...palette.white} />
              <ColorSwatch hex="#000000" name="Black" role="Dark mode background" />
            </div>

            <div style={{
              marginTop: 28, padding: "20px 24px", background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 6,
              borderLeft: "3px solid #E63B2E",
            }}>
              <div style={{ color: "#000", fontSize: 13, fontWeight: 600, marginBottom: 4 }}>Color Rule</div>
              <div style={{ color: "#666", fontSize: 13, lineHeight: 1.6 }}>
                The anvil is black on light backgrounds, white on dark backgrounds — matching the wordmark. Ember red (#E63B2E) appears only on the sparks rising from the anvil and on primary CTAs. This means the icon is nearly monochrome with a single flash of red — the moment of transformation.
              </div>
            </div>
          </div>
        )}

        {tab === "Typography" && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, letterSpacing: -0.3 }}>Type System</h2>
            <p style={{ color: "#666", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              Three typefaces. Manrope for display — geometric, neutral, precise. IBM Plex Mono for technical content — engineered and readable. Instrument Sans for body — clean and warm.
            </p>

            <div style={{ background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 8, padding: "32px 28px", marginBottom: 14 }}>
              <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 24, textTransform: "uppercase" }}>Display — Manrope 700</div>
              {[
                { size: 48, text: "τaoForge" },
                { size: 32, text: "Intelligence Forged on TAO" },
                { size: 24, text: "Recursive Self-Improvement" },
              ].map((s, i) => (
                <div key={i} style={{
                  fontFamily: "'Manrope', sans-serif", fontSize: s.size, fontWeight: 700,
                  color: "#000", letterSpacing: -s.size * 0.015, lineHeight: 1.2, marginBottom: 16,
                }}>{s.text}</div>
              ))}
            </div>

            <div style={{ background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 8, padding: "32px 28px", marginBottom: 14 }}>
              <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 24, textTransform: "uppercase" }}>Mono — IBM Plex Mono 400 / 500</div>
              {[
                { size: 16, text: "proof_of_improvement.verify()", weight: 500, color: "#E63B2E" },
                { size: 14, text: "agent.propose_mutation(delta, bond=2.5)", weight: 400, color: "#1A1A1A" },
                { size: 12, text: "// Verified improvement: +3.4% on bench_v3.2", weight: 400, color: "#999" },
              ].map((s, i) => (
                <div key={i} style={{
                  fontFamily: "'IBM Plex Mono', monospace", fontSize: s.size, fontWeight: s.weight,
                  color: s.color, lineHeight: 1.6, marginBottom: 12,
                }}>{s.text}</div>
              ))}
            </div>

            <div style={{ background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 8, padding: "32px 28px" }}>
              <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 24, textTransform: "uppercase" }}>Body — Instrument Sans 400 / 600</div>
              <div style={{ fontFamily: "'Instrument Sans', sans-serif", fontSize: 16, color: "#000", fontWeight: 600, marginBottom: 8 }}>
                A subnet where agents compete to improve themselves.
              </div>
              <div style={{ fontFamily: "'Instrument Sans', sans-serif", fontSize: 14, color: "#666", lineHeight: 1.7 }}>
                τaoForge creates an economic game where autonomous agents propose mutations to themselves, validators verify the improvements are real, and the evolutionary trajectory becomes a public, verifiable record on the Bittensor network.
              </div>
            </div>
          </div>
        )}

        {tab === "Logo Suite" && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, letterSpacing: -0.3 }}>Logo Variations</h2>
            <p style={{ color: "#666", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              All lockup variants. The anvil matches the wordmark color (black on light, white on dark). Only the sparks carry Ember red.
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
              <div style={{ background: "#fff", border: "1px solid #E0E0E0", borderRadius: 8, padding: 36, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
                <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, textTransform: "uppercase" }}>Light — Horizontal</div>
                <Lockup variant="horizontal" size="md" dark={false} />
              </div>
              <div style={{ background: "#000", border: "1px solid #222", borderRadius: 8, padding: 36, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
                <div style={{ color: "#555", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, textTransform: "uppercase" }}>Dark — Horizontal</div>
                <Lockup variant="horizontal" size="md" dark={true} />
              </div>
              <div style={{ background: "#fff", border: "1px solid #E0E0E0", borderRadius: 8, padding: 36, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
                <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, textTransform: "uppercase" }}>Light — Stacked</div>
                <Lockup variant="stacked" size="md" dark={false} />
              </div>
              <div style={{ background: "#000", border: "1px solid #222", borderRadius: 8, padding: 36, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
                <div style={{ color: "#555", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, textTransform: "uppercase" }}>Dark — Stacked</div>
                <Lockup variant="stacked" size="md" dark={true} />
              </div>
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 36, marginBottom: 16, letterSpacing: -0.2 }}>Icon Only</h3>
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap" }}>
              {[64, 48, 32, 24].map(s => (
                <div key={s} style={{
                  background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 6,
                  width: 88, height: 88, display: "flex", flexDirection: "column",
                  alignItems: "center", justifyContent: "center", gap: 8,
                }}>
                  <ForgeIcon size={s} ember="#E63B2E" />
                  <span style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace" }}>{s}px</span>
                </div>
              ))}
            </div>

            <h3 style={{ fontSize: 16, fontWeight: 700, marginTop: 36, marginBottom: 16, letterSpacing: -0.2 }}>Wordmark Scale</h3>
            <div style={{ background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 8, padding: "28px 32px", display: "flex", flexDirection: "column", gap: 20 }}>
              <Wordmark size="xl" />
              <Wordmark size="lg" />
              <Wordmark size="md" />
              <Wordmark size="sm" />
            </div>
          </div>
        )}

        {tab === "Social Assets" && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, letterSpacing: -0.3 }}>Social & Marketing Assets</h2>
            <p style={{ color: "#666", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              Ready-to-use templates in both light and dark. Light is the default, matching Bittensor's primary context.
            </p>

            <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 10, textTransform: "uppercase" }}>
              X / Twitter Banner — Light — 1500×500
            </div>
            <TwitterBanner />

            <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 10, marginTop: 28, textTransform: "uppercase" }}>
              X / Twitter Banner — Dark — 1500×500
            </div>
            <TwitterBannerDark />

            <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 10, marginTop: 28, textTransform: "uppercase" }}>
              OG Card — Light — 1200×630
            </div>
            <OGCard dark={false} />

            <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 10, marginTop: 28, textTransform: "uppercase" }}>
              OG Card — Dark — 1200×630
            </div>
            <OGCard dark={true} />

            <div style={{ color: "#999", fontSize: 10, fontFamily: "'IBM Plex Mono', monospace", letterSpacing: 2, marginBottom: 10, marginTop: 28, textTransform: "uppercase" }}>
              Profile Pictures
            </div>
            <div style={{ display: "flex", gap: 20, alignItems: "end" }}>
              <AvatarCircle size={100} />
              <AvatarCircle size={100} dark />
              <AvatarCircle size={64} />
              <AvatarCircle size={64} dark />
              <AvatarCircle size={40} />
              <AvatarCircle size={40} dark />
            </div>
          </div>
        )}

        {tab === "Guidelines" && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, letterSpacing: -0.3 }}>Usage Guidelines</h2>
            <p style={{ color: "#666", fontSize: 14, lineHeight: 1.7, marginBottom: 32 }}>
              Rules for maintaining brand consistency. The core principle: black, white, and red anvil. Nothing else.
            </p>

            {[
              {
                title: "DO",
                border: "#000",
                items: [
                  "Use stark white (#FFFFFF) as the primary background — light mode is default",
                  "Reserve Ember red (#E63B2E) exclusively for the sparks in the icon and primary CTAs",
                  "Use pure black (#000000) for all headings and primary text",
                  "Maintain generous whitespace — let the content breathe like bittensor.com",
                  "Always write as 'τaoForge' — lowercase τ (Greek tau), lowercase a-o, capital F",
                  "Use the dark variant (black bg, white text) only for Discord, terminal, and code contexts",
                ],
              },
              {
                title: "DON'T",
                border: "#E63B2E",
                items: [
                  "Don't use Ember red in text, backgrounds, or the anvil body — sparks and CTA only",
                  "Don't add gradients, shadows, or visual effects to the brand — stay flat and stark",
                  "Don't rotate, stretch, or distort the logo or icon",
                  "Don't separate 'Tao' and 'Forge' with a space",
                  "Don't use colored backgrounds behind the logo — white or black only",
                  "Don't introduce additional brand colors — the palette is monochrome + one accent",
                ],
              },
            ].map((section, i) => (
              <div key={i} style={{
                background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 6,
                padding: "24px 28px", marginBottom: 14, borderLeft: `3px solid ${section.border}`,
              }}>
                <div style={{ color: "#000", fontSize: 11, fontWeight: 700, letterSpacing: 2, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 14, textTransform: "uppercase" }}>
                  {section.title}
                </div>
                {section.items.map((item, j) => (
                  <div key={j} style={{ color: "#666", fontSize: 13, lineHeight: 1.6, marginBottom: 6, paddingLeft: 14, borderLeft: "1px solid #E0E0E0" }}>
                    {item}
                  </div>
                ))}
              </div>
            ))}

            <div style={{
              background: "#F5F5F5", border: "1px solid #E0E0E0", borderRadius: 6,
              padding: "24px 28px", marginTop: 24,
            }}>
              <div style={{ color: "#000", fontSize: 11, fontWeight: 700, letterSpacing: 2, fontFamily: "'IBM Plex Mono', monospace", marginBottom: 14, textTransform: "uppercase" }}>
                File Naming Convention
              </div>
              <pre style={{
                color: "#666", fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, lineHeight: 1.8, margin: 0,
              }}>
{`taoforge-logo-horizontal-light.svg
taoforge-logo-horizontal-dark.svg
taoforge-logo-stacked-light.svg
taoforge-logo-stacked-dark.svg
taoforge-icon-64.svg
taoforge-icon-32.svg
taoforge-banner-x-light-1500x500.png
taoforge-banner-x-dark-1500x500.png
taoforge-og-light-1200x630.png
taoforge-og-dark-1200x630.png
taoforge-avatar-light-400x400.png
taoforge-avatar-dark-400x400.png`}
              </pre>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
