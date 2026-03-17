import { useEffect, useRef, Suspense } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Float, MeshDistortMaterial } from '@react-three/drei'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import './index.css'

gsap.registerPlugin(ScrollTrigger)

// ─── 3D Texas Shape ───
function TexasGeo({ scrollRef }) {
  const meshRef = useRef()

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.elapsedTime * 0.15
      meshRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.1) * 0.1
    }
  })

  return (
    <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.5}>
      <mesh ref={meshRef} scale={2.2}>
        <icosahedronGeometry args={[1, 1]} />
        <MeshDistortMaterial
          color="#FF6B00"
          emissive="#FF6B00"
          emissiveIntensity={0.3}
          roughness={0.2}
          metalness={0.8}
          distort={0.25}
          speed={2}
          wireframe={false}
        />
      </mesh>
    </Float>
  )
}

function Scene() {
  return (
    <Canvas camera={{ position: [0, 0, 5], fov: 50 }} style={{ position: 'absolute', inset: 0 }}>
      <ambientLight intensity={0.2} />
      <directionalLight position={[5, 5, 5]} intensity={1} color="#FF6B00" />
      <directionalLight position={[-5, -5, 5]} intensity={0.5} color="#ffffff" />
      <pointLight position={[0, 0, 3]} intensity={0.5} color="#FF6B00" />
      <Suspense fallback={null}>
        <TexasGeo />
      </Suspense>
    </Canvas>
  )
}

// ─── Scroll-triggered section ───
function ScrollSection({ children, className = '', delay = 0 }) {
  const ref = useRef()

  useEffect(() => {
    const el = ref.current
    gsap.fromTo(el,
      { opacity: 0, y: 60 },
      {
        opacity: 1, y: 0, duration: 1, ease: 'power3.out',
        scrollTrigger: { trigger: el, start: 'top 85%', toggleActions: 'play none none none' },
        delay
      }
    )
  }, [delay])

  return <div ref={ref} className={className} style={{ opacity: 0 }}>{children}</div>
}

// ─── Live dot ───
function LiveDot() {
  return (
    <span className="relative flex items-center gap-2">
      <span className="relative flex h-2.5 w-2.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
      </span>
    </span>
  )
}

// ─── Comparison table ───
function ComparisonTable() {
  const rows = [
    ['Focus', 'Texas only', 'National', 'National'],
    ['Contractor phones', 'Included', 'Extra cost', 'Not included'],
    ['Price', 'Free to start', '$96/mo', '$299/mo'],
    ['Updates', 'Real-time', 'Weekly', 'Delayed'],
    ['CSV export', 'Included', 'Included', 'Add-on'],
    ['Contracts', 'None', 'Monthly', 'Annual'],
  ]

  return (
    <div className="glass rounded-2xl overflow-hidden glow-orange">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/10">
            <th className="p-4 text-left text-xs uppercase tracking-wider text-slate-light"></th>
            <th className="p-4 text-center text-xs uppercase tracking-wider text-orange font-bold">Brimstone</th>
            <th className="p-4 text-center text-xs uppercase tracking-wider text-slate">Const. Monitor</th>
            <th className="p-4 text-center text-xs uppercase tracking-wider text-slate">ConstructConnect</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, b, cm, cc], i) => (
            <tr key={i} className="border-b border-white/5">
              <td className="p-4 font-medium text-offwhite">{label}</td>
              <td className="p-4 text-center font-bold text-orange">{b}</td>
              <td className="p-4 text-center text-slate">{cm}</td>
              <td className="p-4 text-center text-slate">{cc}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── City card ───
function CityCard({ name, active = true, href }) {
  return (
    <a
      href={active ? href : undefined}
      className={`glass rounded-xl p-6 text-center transition-all duration-300 ${
        active
          ? 'hover:border-orange/30 hover:shadow-[0_0_30px_rgba(255,107,0,0.1)] cursor-pointer'
          : 'opacity-40 cursor-default'
      }`}
    >
      <div className="flex items-center justify-center gap-2 mb-2">
        {active && <LiveDot />}
        <span className={`text-lg font-semibold ${active ? 'text-offwhite' : 'text-slate'}`}>{name}</span>
      </div>
      <span className={`text-xs uppercase tracking-widest ${active ? 'text-orange' : 'text-slate'}`}>
        {active ? 'Live' : 'Coming soon'}
      </span>
    </a>
  )
}

// ─── Feature card ───
function FeatureCard({ title, description, icon }) {
  return (
    <div className="glass rounded-2xl p-8 hover:border-orange/20 transition-all duration-300">
      <div className="w-12 h-12 rounded-xl bg-orange-dim flex items-center justify-center mb-5 text-2xl">
        {icon}
      </div>
      <h3 className="text-xl font-semibold text-offwhite mb-3">{title}</h3>
      <p className="text-slate-light leading-relaxed text-sm">{description}</p>
    </div>
  )
}

// ─── App ───
export default function App() {
  const DASHBOARD = '/austin-permit-leads/index-dashboard.html'

  useEffect(() => {
    ScrollTrigger.refresh()
  }, [])

  return (
    <div className="relative">
      {/* ── HERO ── */}
      <section className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden">
        <div className="absolute inset-0 z-0 opacity-30">
          <Scene />
        </div>
        {/* Gradient overlay */}
        <div className="absolute inset-0 z-1 bg-gradient-to-b from-transparent via-transparent to-[#0A0A0A]"></div>

        <div className="relative z-10 text-center px-6 max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-xs uppercase tracking-[0.2em] text-slate-light mb-10">
            <LiveDot />
            Brimstone &middot; Texas Construction Intelligence
          </div>

          <h1 className="text-5xl md:text-7xl font-bold leading-[1.05] tracking-tight mb-8">
            <span className="text-offwhite">Know who's building what,</span>
            <br />
            <span className="text-orange">before your competitors.</span>
          </h1>

          <p className="text-lg md:text-xl text-slate-light max-w-2xl mx-auto mb-12 leading-relaxed">
            Every new construction permit filed across Texas &mdash; contractor name, phone number,
            project size, and address. Updated in real time from city records.
          </p>

          <a
            href={DASHBOARD}
            className="inline-flex items-center gap-3 px-8 py-4 bg-orange text-charcoal font-bold rounded-full text-lg hover:shadow-[0_0_40px_rgba(255,107,0,0.3)] transition-all duration-300 hover:-translate-y-1"
          >
            Access the data
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
          </a>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 z-10 animate-bounce">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#8A8A8A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
        </div>
      </section>

      {/* ── LIVE FEED ── */}
      <section className="py-32 px-6">
        <ScrollSection className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-xs uppercase tracking-[0.2em] text-orange mb-8">
            Real-time data
          </div>
          <h2 className="text-3xl md:text-5xl font-bold text-offwhite mb-6 tracking-tight">
            A live feed of<br />construction activity
          </h2>
          <p className="text-slate-light text-lg max-w-xl mx-auto mb-12">
            When a general contractor pulls a building permit, you see it the same day &mdash;
            with their name, phone number, and every project detail.
          </p>
          {/* Mock live feed */}
          <div className="glass rounded-2xl p-1 glow-orange">
            <div className="bg-charcoal rounded-xl p-6 text-left space-y-3">
              {[
                { time: '2 min ago', contractor: 'Harvey-Cleary Builders', type: 'Commercial', sqft: '222,069', addr: '4501 Congress Ave' },
                { time: '18 min ago', contractor: 'Novo Construction', type: 'Commercial', sqft: '191,277', addr: '1200 W 6th St' },
                { time: '1 hr ago', contractor: 'Taylor Morrison', type: 'Residential', sqft: '3,580', addr: '8820 Chalk Knoll Dr' },
                { time: '2 hr ago', contractor: 'Milestone Builders', type: 'Residential', sqft: '4,100', addr: '11400 Manchaca Rd' },
              ].map((item, i) => (
                <div key={i} className="flex items-center justify-between py-3 px-4 rounded-lg hover:bg-charcoal-lighter/50 transition-colors border-b border-white/5 last:border-0">
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-slate w-16">{item.time}</span>
                    <span className="font-semibold text-offwhite">{item.contractor}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${item.type === 'Commercial' ? 'bg-orange-dim text-orange' : 'bg-white/5 text-slate-light'}`}>{item.type}</span>
                    <span className="text-slate-light font-mono">{item.sqft} sqft</span>
                    <span className="text-slate hidden md:block">{item.addr}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </ScrollSection>
      </section>

      {/* ── CITIES ── */}
      <section className="py-32 px-6">
        <ScrollSection className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-xs uppercase tracking-[0.2em] text-orange mb-8">
            Coverage
          </div>
          <h2 className="text-3xl md:text-5xl font-bold text-offwhite mb-6 tracking-tight">
            Across Texas
          </h2>
          <p className="text-slate-light text-lg max-w-xl mx-auto mb-12">
            Live permit data from three major metros. More coming soon.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <CityCard name="Austin" href={`${DASHBOARD}?city=austin`} />
            <CityCard name="San Antonio" href={`${DASHBOARD}?city=sanantonio`} />
            <CityCard name="Dallas" href={`${DASHBOARD}?city=dallas`} />
            <CityCard name="Houston" active={false} />
            <CityCard name="Fort Worth" active={false} />
          </div>
        </ScrollSection>
      </section>

      {/* ── FEATURES ── */}
      <section className="py-32 px-6">
        <ScrollSection className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-xs uppercase tracking-[0.2em] text-orange mb-8">
              How it works
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-offwhite tracking-tight">
              From permit to phone call<br />in 24 hours
            </h2>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            <FeatureCard
              icon={<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>}
              title="Find projects first"
              description="A GC pulls a permit on Monday. You call them Tuesday — before the job hits any bid board. You're first in line."
            />
            <FeatureCard
              icon={<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z"/></svg>}
              title="Call the GC directly"
              description="Every permit includes the general contractor's name, company, and phone number. No middlemen, no bid boards."
            />
            <FeatureCard
              icon={<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF6B00" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>}
              title="Track the big players"
              description="See which contractors are pulling the most permits. Land one relationship with a busy GC and you've got work for months."
            />
          </div>
        </ScrollSection>
      </section>

      {/* ── COMPARISON ── */}
      <section className="py-32 px-6">
        <ScrollSection className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass text-xs uppercase tracking-[0.2em] text-orange mb-8">
              Why Brimstone
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-offwhite tracking-tight mb-4">
              Better data, lower cost
            </h2>
            <p className="text-slate-light text-lg">
              Real-time Texas permit intelligence, free to start. No contracts.
            </p>
          </div>
          <ComparisonTable />
        </ScrollSection>
      </section>

      {/* ── CTA ── */}
      <section className="py-32 px-6">
        <ScrollSection className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl md:text-5xl font-bold text-offwhite tracking-tight mb-6">
            Start finding projects<br /><span className="text-orange">today</span>
          </h2>
          <p className="text-slate-light text-lg mb-12">
            Free access to live permit data across Austin, San Antonio, and Dallas.
            No signup required.
          </p>
          <a
            href={DASHBOARD}
            className="inline-flex items-center gap-3 px-8 py-4 bg-orange text-charcoal font-bold rounded-full text-lg hover:shadow-[0_0_40px_rgba(255,107,0,0.3)] transition-all duration-300 hover:-translate-y-1"
          >
            Access the data
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
          </a>
        </ScrollSection>
      </section>

      {/* ── Footer ── */}
      <footer className="py-12 px-6 border-t border-white/5">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm text-slate">
            Brimstone &middot; Texas Construction Intelligence
          </p>
          <p className="text-xs text-slate mt-2">
            Data sourced from municipal open data portals. Updated continuously.
          </p>
          <a href="mailto:avinash@brimstonepartner.com" className="text-xs text-slate hover:text-orange transition-colors mt-1 inline-block">
            avinash@brimstonepartner.com
          </a>
        </div>
      </footer>
    </div>
  )
}
