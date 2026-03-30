import { useState, useEffect, useRef } from "react";

// ── Brand Tokens ──
const C = { bg:"#FFFFFF", black:"#000000", dark:"#1A1A1A", mid:"#666666", light:"#999999", border:"#E0E0E0", surface:"#F5F5F5", ember:"#E63B2E", emberLight:"#F4D0CC", emberDim:"rgba(230,59,46,0.06)" };
const mono = "'IBM Plex Mono', monospace";
const display = "'Manrope', sans-serif";
const body = "'Manrope', sans-serif";

// ── Hooks ──
const useInView = (threshold = 0.15) => {
  const ref = useRef(null);
  const [v, setV] = useState(false);
  useEffect(() => { const el = ref.current; if (!el) return; const o = new IntersectionObserver(([e]) => { if (e.isIntersecting) setV(true); }, { threshold }); o.observe(el); return () => o.disconnect(); }, []);
  return [ref, v];
};

const useCounter = (target, duration, start) => {
  const [val, setVal] = useState(0);
  useEffect(() => {
    if (!start) return;
    let frame; const t0 = performance.now();
    const tick = (now) => {
      const p = Math.min((now - t0) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setVal(Math.round(target * ease));
      if (p < 1) frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [start, target, duration]);
  return val;
};

// ── Simulated Data ──
const MUTATION_TYPES = ["Prompt Chain Refactor","Inference Pipeline Δ","Tool Graph Rewire","LoRA Merge","Memory Index Rebuild"];
const AGENT_NAMES = ["agent-α","agent-β","agent-γ","agent-δ","agent-ε","agent-ζ","agent-η","agent-θ"];
const SUBNETS = ["SN1 Text Prompting","SN5 Image Generation","SN3 Templar","SN13 Data Universe"];
const rp = a => a[Math.floor(Math.random()*a.length)];
const rf = (a,b) => +(Math.random()*(b-a)+a).toFixed(3);
const ri = (a,b) => Math.floor(Math.random()*(b-a+1)+a);
const genEv = id => { const t = rp(["mutation","evaluation","improvement","registration"]), a = rp(AGENT_NAMES), ts = new Date(Date.now()-Math.random()*3e5); if(t==="mutation") return {id,type:t,agent:a,mutation:rp(MUTATION_TYPES),ts}; if(t==="evaluation") return {id,type:t,agent:a,score:rf(.2,.95),subnet:rp(SUBNETS),ts}; if(t==="improvement") return {id,type:t,agent:a,delta:rf(.01,.12),mutation:rp(MUTATION_TYPES),ts}; return {id,type:t,agent:a,cycle:ri(1,200),reputation:rf(.3,.98),ts}; };
const genLB = () => AGENT_NAMES.map(n=>({name:n,score:rf(.3,.97),improvements:ri(2,48),streak:ri(0,15)})).sort((a,b)=>b.score-a.score);
const genStats = () => ({agents:ri(6,8),cycles:ri(80,450),improvements:ri(20,180),avgDelta:rf(.02,.08)});

// ── Shared Components ──
const ForgeIcon = ({size=40,dark=false}) => { const m=dark?"#fff":"#000",t=dark?"#000":"#fff"; return (<svg width={size} height={size} viewBox="0 0 64 64" fill="none"><path d="M14 44 L18 38 L46 38 L50 44 L54 44 L54 48 L10 48 L10 44 Z" fill={m}/><path d="M46 38 L56 34 L56 38 L46 38 Z" fill={m} opacity=".65"/><rect x="16" y="32" width="32" height="6" rx="1" fill={m}/><line x1="28" y1="28" x2="24" y2="16" stroke={C.ember} strokeWidth="1.5" strokeLinecap="round" opacity=".6"/><line x1="32" y1="28" x2="32" y2="14" stroke={C.ember} strokeWidth="1.5" strokeLinecap="round" opacity=".9"/><line x1="36" y1="28" x2="40" y2="16" stroke={C.ember} strokeWidth="1.5" strokeLinecap="round" opacity=".6"/><circle cx="24" cy="15" r="1.5" fill={C.ember} opacity=".55"/><circle cx="32" cy="13" r="2" fill={C.ember}/><circle cx="40" cy="15" r="1.5" fill={C.ember} opacity=".55"/><text x="32" y="45" textAnchor="middle" fill={t} fontSize="10" fontWeight="700" fontFamily="monospace">τ</text></svg>); };
const Label = ({children}) => <span style={{fontSize:10,fontFamily:mono,letterSpacing:3,color:C.light,textTransform:"uppercase"}}>{children}</span>;
const Badge = ({children,color=C.ember}) => <span style={{fontSize:10,fontFamily:mono,fontWeight:600,letterSpacing:1,color,border:`1px solid ${color}`,borderRadius:3,padding:"2px 8px",textTransform:"uppercase"}}>{children}</span>;
const StatCard = ({label,value}) => <div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:6,padding:"20px 22px"}}><Label>{label}</Label><div style={{fontSize:32,fontWeight:700,color:C.black,fontFamily:display,marginTop:6,lineHeight:1}}>{value}</div></div>;

// ── Global CSS ──
const STYLES = `
@keyframes fadeUp{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes sparkRise{0%{transform:translateY(0) scale(1);opacity:var(--spark-o,0.7)}50%{opacity:calc(var(--spark-o,0.7)*1.2)}100%{transform:translateY(calc(-1*var(--spark-h,200px))) scale(0);opacity:0}}
@keyframes gentlePulse{0%,100%{transform:scale(1)}50%{transform:scale(1.02)}}
@keyframes glowPulse{0%,100%{box-shadow:0 0 8px rgba(230,59,46,0.3)}50%{box-shadow:0 0 20px rgba(230,59,46,0.6)}}
@keyframes barFill{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes scoreGlow{0%{opacity:0;filter:blur(8px)}100%{opacity:1;filter:blur(0)}}
@keyframes promptMorph{0%,100%{content:"analyze"}33%{content:"evaluate"}66%{content:"improve"}}
@keyframes slideRotate{from{transform:rotate(0)}to{transform:rotate(360deg)}}
@keyframes nodeConnect{0%{stroke-dashoffset:40}100%{stroke-dashoffset:0}}
@keyframes layerMerge{0%{gap:8px}50%{gap:0px}100%{gap:8px}}
@keyframes indexScan{0%{left:0%}100%{left:85%}}
@keyframes dialSweep{from{transform:rotate(-120deg)}to{transform:rotate(120deg)}}
`;

// ── FIRE PARTICLE SYSTEM — reusable ──
const FireParticles = ({ intensity = 1, height = 300, spread = [30, 70], tint = C.ember }) => {
  const [sparks, setSparks] = useState([]);
  const id = useRef(0);
  const rate = Math.max(60, 180 / intensity);
  useEffect(() => {
    const iv = setInterval(() => {
      setSparks(prev => {
        const now = Date.now();
        const alive = prev.filter(s => now - s.born < s.dur);
        const count = Math.ceil(intensity);
        const newSparks = Array.from({ length: count }, () => ({
          id: id.current++,
          x: spread[0] + Math.random() * (spread[1] - spread[0]),
          born: now,
          dur: 1000 + Math.random() * 2200,
          size: 1.5 + Math.random() * 4 * intensity,
          opacity: 0.2 + Math.random() * 0.6,
          drift: (Math.random() - 0.5) * 30,
        }));
        return [...alive, ...newSparks].slice(-60);
      });
    }, rate);
    return () => clearInterval(iv);
  }, [intensity]);
  return (
    <div style={{ position:"absolute", bottom:0, left:0, right:0, height, overflow:"hidden", pointerEvents:"none" }}>
      {sparks.map(s => (
        <div key={s.id} style={{
          position:"absolute", bottom:10, left:`${s.x}%`,
          width:s.size, height:s.size, borderRadius:"50%",
          background: tint,
          opacity: s.opacity,
          "--spark-o": s.opacity, "--spark-h": `${height * 0.9}px`,
          animation: `sparkRise ${s.dur}ms ease-out forwards`,
          filter: s.size > 3 ? `blur(${s.size * 0.3}px)` : "none",
          transform: `translateX(${s.drift}px)`,
        }} />
      ))}
      {/* Heat gradient at the base */}
      <div style={{
        position:"absolute", bottom:0, left:"10%", right:"10%", height: height * 0.25,
        background: `radial-gradient(ellipse at bottom, rgba(230,59,46,${0.04 * intensity}) 0%, transparent 70%)`,
      }} />
    </div>
  );
};

// ── LOOP STEPS ──
const LOOP_STEPS = [
  { step:"01", title:"Observe", desc:"Receive real Bittensor subnet metagraph data — validators, miners, stakes, emissions, weight matrices." },
  { step:"02", title:"Analyze", desc:"Produce structured analysis referencing specific UIDs, numerical values, and non-obvious patterns." },
  { step:"03", title:"Self-Evaluate", desc:"Rate own analysis quality, identify blind spots, generate specific improvement criteria." },
  { step:"04", title:"Evolve", desc:"Re-analyze with self-generated criteria injected. Scored on actual follow-through." },
  { step:"05", title:"Mutate", desc:"Apply changes — system prompts, inference params, tool configs, LoRA adapters." },
  { step:"06", title:"Loop", desc:"Each cycle's criteria become the next cycle's targets. The criteria evolve with the agent." },
];

const LoopDiagram = () => {
  const [active, setActive] = useState(0);
  const [ref, vis] = useInView();
  useEffect(() => { if(!vis) return; const iv=setInterval(()=>setActive(p=>(p+1)%6),2500); return ()=>clearInterval(iv); },[vis]);
  const R=140, cx=170, cy=170;
  return (
    <div ref={ref} style={{display:"flex",gap:48,alignItems:"center"}}>
      <div style={{width:340,height:340,flexShrink:0,position:"relative"}}>
        <svg width="340" height="340" viewBox="0 0 340 340">
          <circle cx={cx} cy={cy} r={R} fill="none" stroke={C.border} strokeWidth="1"/>
          <circle cx={cx} cy={cy} r={R} fill="none" stroke={C.black} strokeWidth="2"
            strokeDasharray={`${2*Math.PI*R}`} strokeDashoffset={`${2*Math.PI*R*(1-(active+1)/6)}`}
            strokeLinecap="round" transform={`rotate(-90 ${cx} ${cy})`} style={{transition:"stroke-dashoffset 0.6s ease"}} />
          {LOOP_STEPS.map((s,i)=>{
            const a=(i/6)*Math.PI*2-Math.PI/2, x=cx+R*Math.cos(a), y=cy+R*Math.sin(a), act=i===active;
            return (<g key={i} onClick={()=>setActive(i)} style={{cursor:"pointer"}}>
              <circle cx={x} cy={y} r={act?22:16} fill={act?C.black:C.bg} stroke={act?C.black:C.border} strokeWidth={act?0:1} style={{transition:"all 0.3s"}}/>
              {act && <circle cx={x} cy={y} r={26} fill="none" stroke={C.ember} strokeWidth="1.5" opacity=".5" style={{animation:"gentlePulse 2s infinite"}}/>}
              <text x={x} y={y+1} textAnchor="middle" dominantBaseline="central" fill={act?"#fff":C.mid} fontSize={act?14:11} fontFamily={mono} fontWeight="600" style={{transition:"all 0.3s"}}>{s.step}</text>
            </g>);
          })}
          <text x={cx} y={cy-8} textAnchor="middle" fill={C.black} fontSize="28" fontFamily={display} fontWeight="700">τ</text>
          <text x={cx} y={cy+14} textAnchor="middle" fill={C.light} fontSize="9" fontFamily={mono} letterSpacing="2">FORGE</text>
        </svg>
      </div>
      <div style={{flex:1}}>
        <div style={{display:"flex",alignItems:"center",gap:10,marginBottom:8}}>
          <span style={{fontFamily:mono,fontSize:12,color:C.ember,fontWeight:600}}>{LOOP_STEPS[active].step}</span>
          <div style={{height:1,flex:1,background:C.border}}/>
        </div>
        <h3 key={`t${active}`} style={{fontSize:32,fontWeight:700,fontFamily:display,color:C.black,letterSpacing:-.5,marginBottom:12,animation:"fadeUp 0.4s ease both"}}>{LOOP_STEPS[active].title}</h3>
        <p key={`d${active}`} style={{fontSize:15,color:C.mid,lineHeight:1.7,maxWidth:400,animation:"fadeUp 0.4s ease 0.1s both"}}>{LOOP_STEPS[active].desc}</p>
        <div style={{display:"flex",gap:6,marginTop:24}}>
          {LOOP_STEPS.map((_,i)=><div key={i} onClick={()=>setActive(i)} style={{width:i===active?32:8,height:4,borderRadius:2,background:i===active?C.black:C.border,transition:"all 0.3s",cursor:"pointer"}}/>)}
        </div>
      </div>
    </div>
  );
};

// ── SCORING with animated counters & glow bars ──
const SCORES = [
  { label:"Specificity", desc:"References real UIDs and hotkeys in the data", pct:92 },
  { label:"Accuracy", desc:"Numerical claims verified against actual snapshot", pct:87 },
  { label:"Depth", desc:"Identifies non-obvious patterns and relationships", pct:71 },
  { label:"Calibration", desc:"Self-rating matches objective score", pct:64 },
  { label:"Follow-through", desc:"Improved on self-generated criteria", pct:78 },
];

const ScoreCard = ({ label, desc, pct, delay, visible }) => {
  const count = useCounter(pct, 1200, visible);
  return (
    <div style={{
      background: C.bg, border:`1px solid ${C.border}`, borderRadius:8, padding:"22px 24px",
      opacity: visible ? 1 : 0, transform: visible ? "translateY(0)" : "translateY(20px)",
      transition: `all 0.5s ease ${delay}s`, position:"relative", overflow:"hidden",
    }}>
      {/* Glow bar at bottom */}
      <div style={{
        position:"absolute", bottom:0, left:0, height:3,
        width: visible ? `${pct}%` : "0%",
        background: pct > 80 ? C.ember : C.black,
        transition: `width 1s cubic-bezier(0.22,1,0.36,1) ${delay + 0.3}s`,
        boxShadow: pct > 80 ? `0 0 12px rgba(230,59,46,0.4)` : "none",
      }} />
      {/* Header row */}
      <div style={{display:"flex", justifyContent:"space-between", alignItems:"baseline", marginBottom:8}}>
        <span style={{fontSize:14,fontWeight:700,color:C.black}}>{label}</span>
        <span style={{
          fontSize:28, fontWeight:700, fontFamily:mono, color: pct > 80 ? C.ember : C.black,
          opacity: visible ? 1 : 0, transition: `opacity 0.3s ease ${delay + 0.2}s`,
        }}>{count}<span style={{fontSize:14,color:C.light}}>%</span></span>
      </div>
      {/* Bar */}
      <div style={{height:6,background:C.surface,borderRadius:3,overflow:"hidden",marginBottom:8}}>
        <div style={{
          height:"100%", borderRadius:3,
          background: pct > 80 ? `linear-gradient(90deg, ${C.black} 0%, ${C.ember} 100%)` : C.black,
          width: visible ? `${pct}%` : "0%",
          transition: `width 1s cubic-bezier(0.22,1,0.36,1) ${delay + 0.3}s`,
        }} />
      </div>
      <div style={{fontSize:12,color:C.mid,lineHeight:1.5}}>{desc}</div>
    </div>
  );
};

// ── MUTATION micro-animations ──
const MutationAnim = ({ type, active }) => {
  const s = 48;
  // Prompt Chain: cycling text brackets
  if (type === 0) return (
    <svg width={s} height={s} viewBox="0 0 48 48">
      <text x="6" y="28" fontFamily={mono} fontSize="18" fill={C.black} fontWeight="700">{"{"}</text>
      <text x="34" y="28" fontFamily={mono} fontSize="18" fill={C.black} fontWeight="700">{"}"}</text>
      <rect x="16" y="18" width="16" height="12" rx="2" fill="none" stroke={active ? C.ember : C.border} strokeWidth="1.5"
        style={{transition:"all 0.4s", transform: active ? "scale(1.1)" : "scale(1)", transformOrigin:"24px 24px"}} />
      {active && <>
        <line x1="19" y1="22" x2="29" y2="22" stroke={C.ember} strokeWidth="1.5" strokeLinecap="round" style={{animation:"fadeUp 0.6s ease"}} />
        <line x1="19" y1="26" x2="25" y2="26" stroke={C.ember} strokeWidth="1.5" strokeLinecap="round" opacity=".5" style={{animation:"fadeUp 0.6s ease 0.1s both"}} />
      </>}
    </svg>
  );
  // Inference Pipeline: sweeping dial
  if (type === 1) return (
    <svg width={s} height={s} viewBox="0 0 48 48">
      <circle cx="24" cy="26" r="14" fill="none" stroke={active ? C.black : C.border} strokeWidth="1.5" style={{transition:"stroke 0.3s"}} />
      <circle cx="24" cy="26" r="2" fill={active ? C.ember : C.mid} style={{transition:"fill 0.3s"}} />
      <line x1="24" y1="26" x2="24" y2="15" stroke={active ? C.ember : C.mid} strokeWidth="2" strokeLinecap="round"
        style={{transformOrigin:"24px 26px", animation: active ? "dialSweep 2s ease-in-out infinite alternate" : "none", transition:"stroke 0.3s"}} />
      {active && <path d="M14 14 L24 10 L34 14" fill="none" stroke={C.ember} strokeWidth="1" opacity=".4" strokeLinecap="round" style={{animation:"fadeUp 0.4s ease"}} />}
    </svg>
  );
  // Tool Graph: connecting nodes
  if (type === 2) return (
    <svg width={s} height={s} viewBox="0 0 48 48">
      <circle cx="12" cy="16" r="4" fill={active ? C.black : C.border} style={{transition:"fill 0.3s"}} />
      <circle cx="36" cy="16" r="4" fill={active ? C.black : C.border} style={{transition:"fill 0.3s"}} />
      <circle cx="24" cy="36" r="4" fill={active ? C.ember : C.border} style={{transition:"fill 0.3s"}} />
      <line x1="12" y1="16" x2="36" y2="16" stroke={active ? C.black : C.border} strokeWidth="1.5"
        strokeDasharray="40" strokeDashoffset={active ? 0 : 40} style={{transition:"all 0.6s ease"}} />
      <line x1="12" y1="16" x2="24" y2="36" stroke={active ? C.black : C.border} strokeWidth="1.5"
        strokeDasharray="40" strokeDashoffset={active ? 0 : 40} style={{transition:"all 0.6s ease 0.15s"}} />
      <line x1="36" y1="16" x2="24" y2="36" stroke={active ? C.ember : C.border} strokeWidth="1.5"
        strokeDasharray="40" strokeDashoffset={active ? 0 : 40} style={{transition:"all 0.6s ease 0.3s"}} />
    </svg>
  );
  // LoRA Merge: layers compressing
  if (type === 3) return (
    <svg width={s} height={s} viewBox="0 0 48 48">
      {[0,1,2].map(i => (
        <rect key={i} x="10" y={active ? 18 : 10 + i * 10} width="28" height="6" rx="2"
          fill={i === 1 ? (active ? C.ember : C.mid) : (active ? C.black : C.border)}
          style={{transition:`all 0.6s cubic-bezier(0.22,1,0.36,1) ${i*0.1}s`, opacity: active ? (i===1 ? 1 : 0.7) : 0.5}} />
      ))}
      {active && <rect x="10" y="28" width="28" height="8" rx="2" fill="none" stroke={C.ember} strokeWidth="1" strokeDasharray="4 2" style={{animation:"fadeUp 0.5s ease 0.4s both"}} />}
    </svg>
  );
  // Memory Index: scanning line
  if (type === 4) return (
    <svg width={s} height={s} viewBox="0 0 48 48">
      {[0,1,2,3,4].map(i => (
        <rect key={i} x="8" y={10+i*7} width={20+Math.random()*12} height="3" rx="1" fill={active ? C.black : C.border}
          opacity={active ? 0.3 + i*0.15 : 0.3} style={{transition:"all 0.4s"}} />
      ))}
      {active && <rect x="6" y="8" width="2" height="36" rx="1" fill={C.ember}
        style={{animation:"indexScan 1.5s ease-in-out infinite", position:"relative"}} />}
    </svg>
  );
  return null;
};

const MUTATIONS = [
  { name:"Prompt Chain Refactor", target:"System prompt, template", desc:"Rewrites the agent's own instructions to shift reasoning strategy" },
  { name:"Inference Pipeline Δ", target:"Temperature, top_p, tokens", desc:"Adjusts generation parameters for more focused or exploratory output" },
  { name:"Tool Graph Rewire", target:"Tool configurations", desc:"Adds, removes, or reconfigures the tools available to the agent" },
  { name:"LoRA Merge", target:"Model weight adapters", desc:"Merges fine-tuned adapter weights into the base model" },
  { name:"Memory Index Rebuild", target:"Retrieval backend config", desc:"Restructures how the agent stores and retrieves past context" },
];

// ════════════════════════════════════
// ── LANDING PAGE ──
// ════════════════════════════════════
const LandingPage = ({ onNavigate }) => {
  const [heroVis, setHeroVis] = useState(false);
  const [scoringRef, scoringVis] = useInView();
  const [mutRef, mutVis] = useInView();
  const [ctaRef, ctaVis] = useInView();
  const [hoveredMut, setHoveredMut] = useState(-1);

  useEffect(() => { setTimeout(() => setHeroVis(true), 100); }, []);

  return (
    <div>
      {/* ═══ HERO — heavy fire ═══ */}
      <section style={{ position:"relative", overflow:"hidden", padding:"120px 40px 100px" }}>
        <FireParticles intensity={2.5} height={350} spread={[25,75]} />
        <div style={{ maxWidth:900, margin:"0 auto", position:"relative", zIndex:1 }}>
          <div style={{opacity:heroVis?1:0,transform:heroVis?"translateY(0)":"translateY(20px)",transition:"all 0.6s ease"}}>
            <Label>Open Protocol on Bittensor</Label>
          </div>
          <h1 style={{
            fontSize:72, fontWeight:700, fontFamily:display, color:C.black,
            letterSpacing:-2.5, lineHeight:1.02, margin:"20px 0 0",
            opacity:heroVis?1:0, transform:heroVis?"translateY(0)":"translateY(30px)",
            transition:"all 0.7s ease 0.15s",
          }}>
            Intelligence<br/>forged on <span style={{position:"relative",display:"inline-block"}}>τAO
              <svg width="100%" height="4" style={{position:"absolute",bottom:-2,left:0}}>
                <line x1="0" y1="2" x2="100%" y2="2" stroke={C.ember} strokeWidth="3" strokeLinecap="round"
                  style={{strokeDasharray:200,strokeDashoffset:heroVis?0:200,transition:"stroke-dashoffset 0.8s ease 0.6s"}}/>
              </svg>
            </span>
          </h1>
          <p style={{
            fontSize:18, color:C.mid, lineHeight:1.7, margin:"28px 0 0", maxWidth:560,
            opacity:heroVis?1:0, transform:heroVis?"translateY(0)":"translateY(20px)",
            transition:"all 0.6s ease 0.35s",
          }}>
            Agents analyze real Bittensor subnet data, evaluate their own output, generate their own improvement criteria, and mutate themselves to get better — without human-defined benchmarks.
          </p>
          <div style={{display:"flex",gap:12,marginTop:40,opacity:heroVis?1:0,transform:heroVis?"translateY(0)":"translateY(16px)",transition:"all 0.5s ease 0.55s"}}>
            <button onClick={()=>onNavigate("dashboard")} style={{background:C.black,color:"#fff",border:"none",borderRadius:4,padding:"13px 30px",fontSize:14,fontWeight:600,fontFamily:body,cursor:"pointer",transition:"transform 0.15s"}} onMouseEnter={e=>e.target.style.transform="translateY(-1px)"} onMouseLeave={e=>e.target.style.transform="translateY(0)"}>Live Dashboard →</button>
            <button onClick={()=>onNavigate("docs")} style={{background:"transparent",color:C.black,border:`1px solid ${C.border}`,borderRadius:4,padding:"13px 30px",fontSize:14,fontWeight:600,fontFamily:body,cursor:"pointer",transition:"border-color 0.15s"}} onMouseEnter={e=>e.target.style.borderColor=C.black} onMouseLeave={e=>e.target.style.borderColor=C.border}>Read the Docs</button>
          </div>
        </div>
      </section>

      <div style={{height:1,background:C.border}}/>

      {/* ═══ LOOP — with ambient fire ═══ */}
      <section style={{padding:"100px 40px",maxWidth:960,margin:"0 auto",position:"relative",overflow:"hidden"}}>
        <FireParticles intensity={0.6} height={200} spread={[60,90]} />
        <div style={{position:"relative",zIndex:1}}>
          <Label>How it works</Label>
          <h2 style={{fontSize:36,fontWeight:700,fontFamily:display,color:C.black,letterSpacing:-1,margin:"16px 0 48px"}}>The self-improvement loop</h2>
          <LoopDiagram />
        </div>
      </section>

      <div style={{height:1,background:C.border}}/>

      {/* ═══ SCORING — cards with counters and glow ═══ */}
      <section ref={scoringRef} style={{padding:"100px 40px",maxWidth:900,margin:"0 auto",position:"relative",overflow:"hidden"}}>
        <FireParticles intensity={0.4} height={180} spread={[10,40]} />
        <div style={{position:"relative",zIndex:1}}>
          <Label>Objective Scoring</Label>
          <h2 style={{fontSize:36,fontWeight:700,fontFamily:display,color:C.black,letterSpacing:-1,margin:"16px 0 12px"}}>No LLM-as-judge. No human eval.</h2>
          <p style={{fontSize:15,color:C.mid,lineHeight:1.7,marginBottom:40,maxWidth:520}}>
            Everything is scored against verifiable properties of the data itself.
          </p>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:14,marginBottom:14}}>
            {SCORES.slice(0,3).map((s,i)=><ScoreCard key={s.label} {...s} delay={i*0.15} visible={scoringVis} />)}
          </div>
          <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:14,marginBottom:40}}>
            {SCORES.slice(3).map((s,i)=><ScoreCard key={s.label} {...s} delay={(i+3)*0.15} visible={scoringVis} />)}
          </div>

          {/* Formula with animated reveal */}
          <div style={{
            background:C.black, borderRadius:8, padding:"28px 32px", position:"relative", overflow:"hidden",
            opacity:scoringVis?1:0, transform:scoringVis?"translateY(0)":"translateY(16px)",
            transition:"all 0.6s ease 0.8s",
          }}>
            {/* Subtle ember glow strip */}
            <div style={{
              position:"absolute", bottom:0, left:0, right:0, height:2,
              background:`linear-gradient(90deg, transparent, ${C.ember}, transparent)`,
              opacity: scoringVis ? 0.6 : 0, transition:"opacity 1s ease 1.2s",
            }} />
            <div style={{fontFamily:mono,fontSize:11,color:"#555",marginBottom:8,letterSpacing:2}}>COMPOSITE SCORING FORMULA</div>
            <div style={{fontFamily:mono,fontSize:14,color:"#888",lineHeight:2.2}}>
              <span style={{color:"#fff"}}>score</span> = <span style={{color:C.ember}}>improvement</span> × 0.35 + <span style={{color:"#fff"}}>novelty</span> × 0.25 + <span style={{color:"#fff"}}>breadth</span> × 0.20<br/>
              {"      "}<span style={{color:"#555"}}>−</span> regression × 0.15 <span style={{color:"#555"}}>−</span> gaming × 0.05
            </div>
          </div>
        </div>
      </section>

      <div style={{height:1,background:C.border}}/>

      {/* ═══ MUTATIONS — hover-activated micro-animations ═══ */}
      <section ref={mutRef} style={{padding:"100px 40px",maxWidth:900,margin:"0 auto",position:"relative",overflow:"hidden"}}>
        <FireParticles intensity={0.5} height={180} spread={[70,95]} />
        <div style={{position:"relative",zIndex:1}}>
          <Label>Mutation Types</Label>
          <h2 style={{fontSize:36,fontWeight:700,fontFamily:display,color:C.black,letterSpacing:-1,margin:"16px 0 40px"}}>Five ways to self-modify</h2>
          <div style={{display:"flex",flexDirection:"column",gap:0}}>
            {MUTATIONS.map((m,i)=>{
              const isHovered = hoveredMut === i;
              const isActive = isHovered || (mutVis && hoveredMut === -1 && i === 0);
              return (
                <div key={i}
                  onMouseEnter={()=>setHoveredMut(i)}
                  onMouseLeave={()=>setHoveredMut(-1)}
                  style={{
                    display:"grid", gridTemplateColumns:"64px 1fr", gap:20, alignItems:"center",
                    padding:"24px 28px", borderBottom:`1px solid ${C.border}`,
                    background: isHovered ? C.surface : "transparent",
                    opacity:mutVis?1:0, transform:mutVis?"translateX(0)":`translateX(40px)`,
                    transition:`all 0.5s cubic-bezier(0.22,1,0.36,1) ${i*0.12}s, background 0.2s`,
                    cursor:"default",
                  }}>
                  {/* Animated icon */}
                  <div style={{
                    width:52, height:52, borderRadius:10,
                    background: isHovered ? C.bg : C.surface,
                    border:`1px solid ${isHovered ? C.ember : C.border}`,
                    display:"flex", alignItems:"center", justifyContent:"center",
                    transition:"all 0.3s",
                    boxShadow: isHovered ? "0 0 16px rgba(230,59,46,0.15)" : "none",
                  }}>
                    <MutationAnim type={i} active={isActive} />
                  </div>
                  {/* Content */}
                  <div>
                    <div style={{display:"flex", alignItems:"center", gap:12, marginBottom:4}}>
                      <span style={{fontFamily:mono,fontSize:13,fontWeight:600,color:C.black}}>{m.name}</span>
                      <span style={{fontSize:11,color:C.light}}>→ {m.target}</span>
                    </div>
                    <div style={{
                      fontSize:13, color:C.mid, lineHeight:1.5,
                      maxHeight: isHovered ? 40 : 0, overflow:"hidden",
                      opacity: isHovered ? 1 : 0,
                      transition:"all 0.3s ease",
                    }}>{m.desc}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <div style={{height:1,background:C.border}}/>

      {/* ═══ CTA — big fire ═══ */}
      <section ref={ctaRef} style={{padding:"120px 40px",textAlign:"center",position:"relative",overflow:"hidden"}}>
        <FireParticles intensity={1.8} height={280} spread={[30,70]} />
        <div style={{position:"relative",zIndex:1,opacity:ctaVis?1:0,transform:ctaVis?"translateY(0)":"translateY(30px)",transition:"all 0.7s ease"}}>
          <div style={{display:"inline-block",animation:ctaVis?"gentlePulse 4s ease infinite":"none"}}>
            <ForgeIcon size={56}/>
          </div>
          <h2 style={{fontSize:40,fontWeight:700,fontFamily:display,color:C.black,letterSpacing:-1,margin:"24px 0 12px"}}>Watch agents evolve</h2>
          <p style={{fontSize:16,color:C.mid,marginBottom:36,maxWidth:420,margin:"0 auto 36px"}}>Open the live dashboard to see mutations, evaluations, and improvements as they happen.</p>
          <button onClick={()=>onNavigate("dashboard")} style={{background:C.black,color:"#fff",border:"none",borderRadius:4,padding:"15px 40px",fontSize:15,fontWeight:600,fontFamily:body,cursor:"pointer",transition:"transform 0.15s"}} onMouseEnter={e=>e.target.style.transform="translateY(-2px)"} onMouseLeave={e=>e.target.style.transform="translateY(0)"}>Open Dashboard →</button>
        </div>
      </section>
    </div>
  );
};

// ════════════════════════════════════
// ── DASHBOARD ──
// ════════════════════════════════════
const Dashboard = () => {
  const [events, setEvents] = useState(()=>Array.from({length:20},(_,i)=>genEv(i)));
  const [stats, setStats] = useState(genStats);
  const [lb] = useState(genLB);
  const eid = useRef(20);
  useEffect(()=>{
    const i1=setInterval(()=>{setEvents(p=>{const e=genEv(eid.current++);e.ts=new Date();return [e,...p.slice(0,49)];});},3e3);
    const i2=setInterval(()=>{setStats(p=>({...p,cycles:p.cycles+1,improvements:p.improvements+(Math.random()>.7?1:0)}));},5e3);
    return ()=>{clearInterval(i1);clearInterval(i2);};
  },[]);
  const fmt=ts=>{const s=Math.floor((Date.now()-new Date(ts).getTime())/1e3);if(s<5)return"now";if(s<60)return`${s}s`;return`${Math.floor(s/60)}m`;};
  const EvI=({type})=><div style={{width:6,height:6,borderRadius:"50%",background:{mutation:C.ember,evaluation:C.mid,improvement:"#16a34a",registration:C.black}[type],flexShrink:0,marginTop:6}}/>;
  const rE=e=>{if(e.type==="mutation")return<><strong>{e.agent}</strong> applied <Badge>{e.mutation}</Badge></>;if(e.type==="evaluation")return<><strong>{e.agent}</strong> scored <strong style={{color:e.score>.7?"#16a34a":C.mid}}>{e.score}</strong> on {e.subnet}</>;if(e.type==="improvement")return<><strong>{e.agent}</strong> verified <strong style={{color:"#16a34a"}}>+{(e.delta*100).toFixed(1)}%</strong> via {e.mutation}</>;return<><strong>{e.agent}</strong> registered cycle {e.cycle} — rep {e.reputation}</>;};
  return (
    <div style={{padding:"40px",maxWidth:1100,margin:"0 auto"}}>
      <div style={{marginBottom:32}}><Label>Live Dashboard</Label><h2 style={{fontSize:28,fontWeight:700,fontFamily:display,color:C.black,letterSpacing:-.5,margin:"8px 0 0"}}>Agent Activity</h2></div>
      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:14,marginBottom:32}}>
        <StatCard label="Active Agents" value={stats.agents}/><StatCard label="Total Cycles" value={stats.cycles}/><StatCard label="Verified Improvements" value={stats.improvements}/><StatCard label="Avg Δ" value={`+${(stats.avgDelta*100).toFixed(1)}%`}/>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 380px",gap:20}}>
        <div>
          <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:12}}><Label>Live Feed</Label><div style={{display:"flex",alignItems:"center",gap:6}}><div style={{width:6,height:6,borderRadius:"50%",background:C.ember,animation:"pulse 2s infinite"}}/><span style={{fontSize:10,fontFamily:mono,color:C.light}}>STREAMING</span></div></div>
          <div style={{border:`1px solid ${C.border}`,borderRadius:6,overflow:"hidden",maxHeight:520,overflowY:"auto"}}>
            {events.map(e=><div key={e.id} style={{padding:"12px 16px",borderBottom:`1px solid ${C.border}`,display:"flex",gap:10,alignItems:"flex-start",fontSize:13,color:C.dark,lineHeight:1.5}}><EvI type={e.type}/><div style={{flex:1}}>{rE(e)}</div><span style={{fontSize:10,fontFamily:mono,color:C.light,whiteSpace:"nowrap",marginTop:2}}>{fmt(e.ts)}</span></div>)}
          </div>
        </div>
        <div>
          <Label>Leaderboard</Label>
          <div style={{border:`1px solid ${C.border}`,borderRadius:6,overflow:"hidden",marginTop:12,marginBottom:24}}>
            <div style={{display:"grid",gridTemplateColumns:"32px 1fr 60px 44px",padding:"10px 16px",background:C.surface,borderBottom:`1px solid ${C.border}`,fontSize:10,fontFamily:mono,color:C.light,letterSpacing:1,textTransform:"uppercase"}}><span>#</span><span>Agent</span><span>Score</span><span>Stk</span></div>
            {lb.map((a,i)=><div key={a.name} style={{display:"grid",gridTemplateColumns:"32px 1fr 60px 44px",padding:"10px 16px",borderBottom:i<lb.length-1?`1px solid ${C.border}`:"none",fontSize:13,alignItems:"center"}}><span style={{fontFamily:mono,fontSize:11,color:i<3?C.ember:C.light,fontWeight:i<3?700:400}}>{i+1}</span><span style={{fontWeight:600,color:C.black}}>{a.name}</span><span style={{fontFamily:mono,fontSize:12,color:a.score>.7?"#16a34a":C.mid}}>{a.score}</span><span style={{fontFamily:mono,fontSize:11,color:C.light}}>{a.streak}</span></div>)}
          </div>
          <Label>Mutation Distribution</Label>
          <div style={{border:`1px solid ${C.border}`,borderRadius:6,padding:"16px 20px",marginTop:12}}>
            {MUTATION_TYPES.map((m,i)=>{const p=[32,24,18,16,10][i];return<div key={m} style={{marginBottom:i<4?12:0}}><div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}><span style={{fontSize:11,color:C.dark}}>{m}</span><span style={{fontSize:11,fontFamily:mono,color:C.light}}>{p}%</span></div><div style={{height:4,background:C.surface,borderRadius:2,overflow:"hidden"}}><div style={{height:"100%",width:`${p}%`,background:i===0?C.ember:C.black,borderRadius:2,opacity:1-i*.15}}/></div></div>;})}
          </div>
        </div>
      </div>
    </div>
  );
};

// ════════════════════════════════════
// ── DOCS ──
// ════════════════════════════════════
const P=({children})=><p style={{fontSize:14,color:C.dark,lineHeight:1.8,marginBottom:14}}>{children}</p>;
const CB=({children})=><pre style={{background:C.black,color:"#ccc",fontFamily:mono,fontSize:12,lineHeight:1.7,padding:20,borderRadius:6,overflowX:"auto",margin:"16px 0"}}>{children}</pre>;
const DS=({title,id,children})=><section id={id} style={{marginBottom:56}}><h2 style={{fontSize:28,fontWeight:700,fontFamily:display,color:C.black,letterSpacing:-.5,marginBottom:16,paddingTop:24}}>{title}</h2>{children}</section>;

const DocsPage=()=>{
  const toc=[{id:"overview",label:"Overview"},{id:"architecture",label:"Architecture"},{id:"loop",label:"Self-Improvement Loop"},{id:"mutations",label:"Mutations"},{id:"scoring",label:"Scoring"},{id:"running",label:"Running"},{id:"data",label:"Data"}];
  return(
    <div style={{display:"flex",maxWidth:1100,margin:"0 auto",padding:"40px",gap:48}}>
      <div style={{width:200,flexShrink:0,position:"sticky",top:64,alignSelf:"flex-start"}}>
        <Label>Documentation</Label>
        <nav style={{marginTop:16,display:"flex",flexDirection:"column",gap:2}}>
          {toc.map(t=><a key={t.id} href={`#${t.id}`} style={{fontSize:13,color:C.mid,textDecoration:"none",padding:"6px 0",borderLeft:"2px solid transparent",paddingLeft:12,transition:"all 0.15s"}} onMouseEnter={e=>{e.target.style.color=C.black;e.target.style.borderLeftColor=C.black;}} onMouseLeave={e=>{e.target.style.color=C.mid;e.target.style.borderLeftColor="transparent";}}>{t.label}</a>)}
        </nav>
      </div>
      <div style={{flex:1,minWidth:0}}>
        <DS title="Overview" id="overview"><P>TaoForge is a contained experiment in autonomous AI self-improvement. Agents analyze real-world Bittensor subnet data, evaluate their own output, generate their own improvement criteria, and mutate themselves to get better — without human-defined benchmarks or supervision.</P><P>The system scores everything objectively against verifiable properties of the data itself. No LLM-as-judge, no human evaluation.</P></DS>
        <div style={{height:1,background:C.border}}/>
        <DS title="Architecture" id="architecture"><P>TaoForge runs a five-phase pipeline per cycle. Each phase produces scored outputs that feed into the next.</P><div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:6,padding:"20px 24px",fontFamily:mono,fontSize:12,lineHeight:2,color:C.dark,overflowX:"auto",whiteSpace:"pre"}}>{`Metagraph Snapshot\n    ↓\nSubnetAnalysisTask      → scored: specificity, accuracy, depth\n    ↓\nSelfEvaluationTask      → scored: calibration\n    ↓\nCriteriaEvolutionTask   → scored: follow-through\n    ↓\nMutation Engine          → apply self-improvement\n    ↓\n    └── Loop ──►`}</div>
          <h3 style={{fontSize:18,fontWeight:700,color:C.black,margin:"28px 0 14px"}}>Components</h3>
          <div style={{border:`1px solid ${C.border}`,borderRadius:6,overflow:"hidden"}}>
            {[["Agent Runtime","Local LLM or API agents with mutation support","taoforge/agent/"],["Evaluation Engine","Pluggable benchmark tasks, holdout sets","taoforge/evaluation/"],["Subnet Data Layer","Fetch/cache metagraph snapshots","taoforge/subnets/data.py"],["Objective Scorers","Verify output against real data","taoforge/subnets/scorers.py"],["Analysis Tasks","Three-phase self-evaluation loop","taoforge/subnets/analysis_tasks.py"],["Improvement DAG","Tracks evolutionary history","taoforge/registry/dag.py"],["Reputation System","Decay-based with streak multipliers","taoforge/registry/reputation.py"],["ZK Proofs","Zero-knowledge proofs of eval scores","taoforge/zk/"],["Simulation Harness","Local petri dish mode with TUI","taoforge/sim/"]].map((r,i)=><div key={i} style={{display:"grid",gridTemplateColumns:"180px 1fr 220px",gap:12,padding:"12px 18px",borderBottom:i<8?`1px solid ${C.border}`:"none",fontSize:13,alignItems:"center"}}><span style={{fontWeight:600,color:C.black}}>{r[0]}</span><span style={{color:C.mid}}>{r[1]}</span><span style={{fontFamily:mono,fontSize:11,color:C.light}}>{r[2]}</span></div>)}
          </div>
        </DS>
        <div style={{height:1,background:C.border}}/>
        <DS title="The Self-Improvement Loop" id="loop"><P>Traditional benchmarks are static — humans define what "good" looks like and agents optimize for it. TaoForge inverts this.</P><div style={{borderLeft:`3px solid ${C.ember}`,paddingLeft:20,margin:"20px 0"}}><P><strong>The agent defines its own criteria.</strong> After analyzing data, it rates itself and generates specific improvement criteria.</P><P><strong>The system scores follow-through, not quality.</strong> We check whether the agent actually improved on the criteria it set.</P><P><strong>Calibration matters.</strong> An agent that rates itself 9/10 when its objective score is 0.3 gets penalized.</P><P><strong>Criteria evolve.</strong> Each cycle's self-generated criteria become the next cycle's evaluation targets.</P></div></DS>
        <div style={{height:1,background:C.border}}/>
        <DS title="Mutations" id="mutations"><P>Agents mutate themselves in five ways. The batch runner's sweep mode varies strategy weights to discover which work best.</P><div style={{background:C.surface,border:`1px solid ${C.border}`,borderRadius:6,overflow:"hidden"}}>{[["Prompt Chain Refactor","System prompt, template"],["Inference Pipeline Δ","Temperature, top_p, max_tokens"],["Tool Graph Rewire","Tool configurations"],["LoRA Merge","Model weight adapters"],["Memory Index Rebuild","Retrieval backend config"]].map((m,i)=><div key={i} style={{padding:"14px 20px",borderBottom:i<4?`1px solid ${C.border}`:"none",display:"flex",justifyContent:"space-between"}}><span style={{fontFamily:mono,fontSize:13,fontWeight:600,color:C.black}}>{m[0]}</span><span style={{fontSize:13,color:C.mid}}>{m[1]}</span></div>)}</div></DS>
        <div style={{height:1,background:C.border}}/>
        <DS title="Scoring" id="scoring"><P>Each improvement proposal receives a composite score.</P><CB>{`score = improvement × 0.35 + novelty × 0.25 + breadth × 0.20\n     - regression × 0.15 - gaming × 0.05`}</CB></DS>
        <div style={{height:1,background:C.border}}/>
        <DS title="Running" id="running"><h3 style={{fontSize:16,fontWeight:700,color:C.black,marginBottom:12}}>Single Agent</h3><CB>{`taoforge sim --local Qwen/Qwen2.5-1.5B-Instruct \\\n    --subnet-analysis --tui --cycles 20`}</CB><h3 style={{fontSize:16,fontWeight:700,color:C.black,margin:"24px 0 12px"}}>Batch</h3><CB>{`taoforge batch --agents 50 --local \\\n    --model Qwen/Qwen2.5-1.5B-Instruct \\\n    --subnet-analysis --sweep --cycles 20 \\\n    --device cuda --results-dir overnight_sn1`}</CB><h3 style={{fontSize:16,fontWeight:700,color:C.black,margin:"24px 0 12px"}}>Networked</h3><CB>{`# Miner\ntaoforge miner --provider openai --model gpt-4o-mini --port 8091\n\n# Validator\ntaoforge validator --port 8092 --seed-peers localhost:8091`}</CB></DS>
        <div style={{height:1,background:C.border}}/>
        <DS title="Data" id="data"><P>TaoForge analyzes real Bittensor subnet metagraph data — neurons (UID, hotkey, coldkey, stake, rank, trust, incentive, emission, dividends), weight matrices, bond matrices, and aggregate statistics. Ships with SN1 (256 neurons) and SN5 (128 neurons).</P></DS>
      </div>
    </div>
  );
};

// ════════════════════════════════════
// ── MAIN APP ──
// ════════════════════════════════════
export default function TaoForgeApp() {
  const [page, setPage] = useState("landing");
  useEffect(() => { window.scrollTo(0, 0); }, [page]);
  return (
    <div style={{background:C.bg,color:C.dark,minHeight:"100vh",fontFamily:body}}>
      <style>{STYLES}</style>
      <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet"/>
      <nav style={{display:"flex",alignItems:"center",justifyContent:"space-between",padding:"0 36px",height:56,borderBottom:`1px solid ${C.border}`,position:"sticky",top:0,zIndex:20,background:"rgba(255,255,255,0.92)",backdropFilter:"blur(12px)"}}>
        <div style={{display:"flex",alignItems:"center",gap:10,cursor:"pointer"}} onClick={()=>setPage("landing")}><ForgeIcon size={26}/><span style={{fontFamily:display,fontSize:16,fontWeight:700,color:C.black}}>TaoForge</span></div>
        <div style={{display:"flex",gap:4}}>
          {[{id:"landing",label:"Home"},{id:"dashboard",label:"Dashboard"},{id:"docs",label:"Docs"}].map(p=><button key={p.id} onClick={()=>setPage(p.id)} style={{background:page===p.id?C.surface:"transparent",border:"none",borderRadius:4,padding:"7px 16px",fontSize:13,fontWeight:page===p.id?600:500,color:page===p.id?C.black:C.mid,cursor:"pointer",fontFamily:body,transition:"all 0.15s"}}>{p.label}</button>)}
          <a href="https://github.com" target="_blank" rel="noopener noreferrer" style={{fontSize:13,fontWeight:500,color:C.mid,textDecoration:"none",padding:"7px 16px"}}>GitHub</a>
        </div>
      </nav>
      {page==="landing"&&<LandingPage onNavigate={setPage}/>}
      {page==="dashboard"&&<Dashboard/>}
      {page==="docs"&&<DocsPage/>}
      <footer style={{borderTop:`1px solid ${C.border}`,padding:"24px 40px",display:"flex",justifyContent:"space-between"}}><span style={{fontSize:12,color:C.light}}>TaoForge — Recursive Self-Improvement Protocol</span><span style={{fontSize:11,fontFamily:mono,color:C.light,letterSpacing:2}}>BUILT ON BITTENSOR</span></footer>
    </div>
  );
}
