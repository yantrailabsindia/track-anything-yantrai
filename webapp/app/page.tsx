'use client';

import Link from "next/link";
import { useState, useEffect } from "react";
import { Activity, Download, Shield, Zap, BarChart3, Clock, Users, Smartphone, Share, PlusSquare, MoreVertical, Menu, X } from "lucide-react";
import { getDeviceInfo, isStandaloneMode } from "@/pwa/lib/pwa-utils";

export default function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [showInstallGuide, setShowInstallGuide] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);

  useEffect(() => {
    const { isIOS: ios, isAndroid: android } = getDeviceInfo();
    setIsIOS(ios);
    // Detect mobile: user agent OR touch screen with small viewport
    const isTouchMobile = ios || android || (
      'ontouchstart' in window && window.innerWidth < 768
    );
    setIsMobile(isTouchMobile);
    setIsInstalled(isStandaloneMode());

    const handleBeforeInstallPrompt = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e);
    };
    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
  }, []);

  const handleInstallClick = async () => {
    if (deferredPrompt) {
      // Android Chrome - use native prompt
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setDeferredPrompt(null);
      }
    } else {
      // iOS or other - show manual guide
      setShowInstallGuide(true);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      background: "radial-gradient(ellipse at top, rgba(79,70,229,0.12), #0a0a0c 60%)"
    }}>
      {/* Mobile-friendly Navigation */}
      <nav style={{
        position: "fixed", top: 0, left: 0, right: 0,
        padding: "12px 16px",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        zIndex: 50, backdropFilter: "blur(12px)",
        background: "rgba(10,10,12,0.85)",
        borderBottom: "1px solid rgba(255,255,255,0.06)"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div className="primary-gradient" style={{ width: 36, height: 36, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Activity color="white" size={18} />
          </div>
          <span style={{ fontSize: 20, fontWeight: 800, letterSpacing: "-0.03em" }}>ProMe</span>
        </div>

        {/* Desktop nav links */}
        <div className="desktop-nav-links" style={{ gap: 32, alignItems: "center" }}>
          <a href="#features" style={{ color: "#94a3b8", fontSize: 14, fontWeight: 600 }}>Features</a>
          <a href="#roles" style={{ color: "#94a3b8", fontSize: 14, fontWeight: 600 }}>For Teams</a>
          <Link href="/login">
            <button className="btn-primary" style={{ display: "flex", alignItems: "center", gap: 8, boxShadow: "0 10px 30px rgba(79,70,229,0.3)" }}>
              Sign In
            </button>
          </Link>
        </div>

        {/* Mobile nav buttons */}
        <div style={{ gap: 8, alignItems: "center" }} className="mobile-nav-buttons">
          <Link href="/login">
            <button className="btn-primary" style={{ padding: "8px 16px", fontSize: 14 }}>
              Sign In
            </button>
          </Link>
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            style={{ background: "none", border: "none", color: "var(--foreground)", padding: 8, cursor: "pointer" }}
            aria-label="Menu"
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </nav>

      {/* Mobile dropdown menu */}
      {menuOpen && (
        <div style={{
          position: "fixed", top: 60, left: 0, right: 0, zIndex: 49,
          background: "rgba(10,10,12,0.95)", backdropFilter: "blur(12px)",
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          padding: "12px 16px",
          display: "flex", flexDirection: "column", gap: 4
        }}>
          <a href="#features" onClick={() => setMenuOpen(false)} style={{ color: "#94a3b8", fontSize: 15, fontWeight: 600, padding: "12px 8px", borderRadius: 8 }}>Features</a>
          <a href="#roles" onClick={() => setMenuOpen(false)} style={{ color: "#94a3b8", fontSize: 15, fontWeight: 600, padding: "12px 8px", borderRadius: 8 }}>For Teams</a>
          {isMobile && !isInstalled && (
            <button
              onClick={() => { setMenuOpen(false); handleInstallClick(); }}
              style={{ color: "#818cf8", fontSize: 15, fontWeight: 600, padding: "12px 8px", borderRadius: 8, background: "none", border: "none", textAlign: "left", cursor: "pointer" }}
            >
              <Download size={16} style={{ display: "inline", marginRight: 8, verticalAlign: "middle" }} />
              Install App
            </button>
          )}
        </div>
      )}

      {/* Main Content */}
      <main style={{ textAlign: "center", maxWidth: 900, margin: "0 auto", padding: "80px 20px 32px", width: "100%" }}>
        <div className="glass" style={{ display: "inline-flex", alignItems: "center", gap: 8, padding: "8px 16px", borderRadius: 999, fontSize: 13, fontWeight: 600, color: "var(--primary)", marginBottom: 24 }}>
          <Zap size={14} fill="currentColor" />
          <span>Enterprise Ready — Deploy on 100+ Systems</span>
        </div>

        <h1 style={{ fontSize: "clamp(32px, 7vw, 68px)", fontWeight: 900, letterSpacing: "-0.04em", lineHeight: 1.05, marginBottom: 20 }}>
          Your Team&apos;s<br />
          <span className="text-gradient">Productivity</span>,<br className="mobile-br" /> Visualized
        </h1>

        <p style={{ fontSize: "clamp(14px, 3.5vw, 18px)", color: "#94a3b8", marginBottom: 32, maxWidth: 540, margin: "0 auto 32px", lineHeight: 1.7, padding: "0 8px" }}>
          ProMe is a silent productivity assistant that sits on every employee&apos;s laptop, tracking focus and activity without disruption.
          Admins get real-time dashboards. Employees get personal insights.
        </p>

        {/* CTA Buttons */}
        <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap", padding: "0 8px" }}>
          <Link href="/login">
            <button className="btn-primary" style={{ padding: "14px 28px", fontSize: 16, display: "flex", alignItems: "center", gap: 10, boxShadow: "0 10px 30px rgba(79,70,229,0.3)", width: "100%", justifyContent: "center" }}>
              Get Started
            </button>
          </Link>

          {/* Install App button - only show on mobile when not installed */}
          {isMobile && !isInstalled && (
            <button
              onClick={handleInstallClick}
              style={{
                padding: "14px 28px", fontSize: 16, display: "flex", alignItems: "center", gap: 10,
                background: "rgba(79,70,229,0.15)", color: "#818cf8",
                border: "1px solid rgba(79,70,229,0.3)", borderRadius: 12,
                fontWeight: 600, cursor: "pointer", width: "100%", justifyContent: "center"
              }}
            >
              <Download size={20} /> Install as App
            </button>
          )}
        </div>

        {/* Install Guide Modal */}
        {showInstallGuide && (
          <div style={{
            position: "fixed", top: 0, left: 0, right: 0, bottom: 0, zIndex: 100,
            background: "rgba(0,0,0,0.8)", backdropFilter: "blur(8px)",
            display: "flex", alignItems: "flex-end", justifyContent: "center",
            padding: "0 0 0 0"
          }} onClick={() => setShowInstallGuide(false)}>
            <div style={{
              background: "#1a1a2e", borderRadius: "24px 24px 0 0",
              padding: "24px 20px 36px", width: "100%", maxWidth: 480,
              borderTop: "1px solid rgba(255,255,255,0.1)"
            }} onClick={(e) => e.stopPropagation()}>
              <div style={{ width: 40, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.2)", margin: "0 auto 20px" }} />
              <h3 style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>Install YantrAI App</h3>
              <p style={{ color: "#94a3b8", fontSize: 14, marginBottom: 20 }}>Follow these steps to add the app to your home screen:</p>

              {isIOS ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <InstallStep number={1} icon={<Share size={20} color="#818cf8" />} text='Tap the Share button at the bottom of Safari' />
                  <InstallStep number={2} icon={<PlusSquare size={20} color="#818cf8" />} text='Scroll down and tap "Add to Home Screen"' />
                  <InstallStep number={3} icon={<Activity size={20} color="#818cf8" />} text='Tap "Add" — the app will appear on your home screen' />
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                  <InstallStep number={1} icon={<MoreVertical size={20} color="#818cf8" />} text='Tap the menu button (⋮) in your browser' />
                  <InstallStep number={2} icon={<Download size={20} color="#818cf8" />} text='Tap "Install app" or "Add to Home Screen"' />
                  <InstallStep number={3} icon={<Activity size={20} color="#818cf8" />} text='Tap "Install" — the app will appear on your home screen' />
                </div>
              )}

              <button
                onClick={() => setShowInstallGuide(false)}
                style={{
                  marginTop: 24, width: "100%", padding: "14px",
                  background: "var(--primary)", color: "white",
                  border: "none", borderRadius: 12, fontWeight: 600,
                  fontSize: 16, cursor: "pointer"
                }}
              >
                Got it
              </button>
            </div>
          </div>
        )}

        {/* Features */}
        <div id="features" style={{ marginTop: 72, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16, textAlign: "left" }}>
          <FeatureCard icon={<Shield color="var(--primary)" />} title="Privacy First" desc="Counts keystrokes, not content. No keylogging. Your data, your control." />
          <FeatureCard icon={<BarChart3 color="var(--accent)" />} title="Real-time Analytics" desc="Beautiful charts showing where time and energy goes across your team." />
          <FeatureCard icon={<Clock color="#10b981" />} title="Silent Tracking" desc="Zero friction. Runs from boot, sits in the tray, and just works." />
          <FeatureCard icon={<Users color="#f59e0b" />} title="Team Management" desc="Admin panel to manage employees, view org-wide productivity, and drill down." />
          <FeatureCard icon={<Smartphone color="#ec4899" />} title="Mobile App" desc="Check your team's productivity from your phone with AI-powered insights." />
          <FeatureCard icon={<Download color="#06b6d4" />} title="Easy Deployment" desc="One .exe installer. Push to 100 systems with a single script." />
        </div>

        {/* Role Comparison */}
        <div id="roles" style={{ marginTop: 64, marginBottom: 32 }}>
          <h2 style={{ fontSize: "clamp(22px, 5vw, 36px)", fontWeight: 800, marginBottom: 32, letterSpacing: "-0.02em" }}>Two Views, One Platform</h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16, textAlign: "left" }}>
            <div className="card" style={{ borderTop: "3px solid var(--primary)" }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
                <Shield size={18} color="var(--primary)" /> Admin / Team Lead
              </h3>
              <ul style={{ color: "#94a3b8", fontSize: 14, lineHeight: 2.2, paddingLeft: 20 }}>
                <li>See all employees on one screen</li>
                <li>Org-wide productivity score</li>
                <li>Individual employee drill-down</li>
                <li>Screenshot verification</li>
                <li>Add/remove employees</li>
                <li>Download .exe for distribution</li>
              </ul>
            </div>
            <div className="card" style={{ borderTop: "3px solid #10b981" }}>
              <h3 style={{ fontSize: 18, fontWeight: 700, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
                <Activity size={18} color="#10b981" /> Employee
              </h3>
              <ul style={{ color: "#94a3b8", fontSize: 14, lineHeight: 2.2, paddingLeft: 20 }}>
                <li>Personal productivity score</li>
                <li>Your own activity timeline</li>
                <li>Hourly activity chart</li>
                <li>Top apps breakdown</li>
                <li>Your screenshots</li>
                <li>Download agent for your laptop</li>
              </ul>
            </div>
          </div>
        </div>
      </main>

      <footer style={{ padding: "24px 16px", color: "#475569", fontSize: 13, textAlign: "center" }}>
        © 2026 ProMe Assistant by YantrAI. Enterprise Productivity Intelligence.
      </footer>
    </div>
  );
}

function InstallStep({ number, icon, text }: { number: number, icon: any, text: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
      <div style={{
        width: 40, height: 40, borderRadius: 12,
        background: "rgba(79,70,229,0.15)", display: "flex",
        alignItems: "center", justifyContent: "center", flexShrink: 0
      }}>
        {icon}
      </div>
      <div>
        <span style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600 }}>Step {number}</span>
        <p style={{ fontSize: 15, fontWeight: 500, lineHeight: 1.4 }}>{text}</p>
      </div>
    </div>
  );
}

function FeatureCard({ icon, title, desc }: { icon: any, title: string, desc: string }) {
  return (
    <div className="card" style={{ textAlign: "left" }}>
      <div style={{ marginBottom: 12, padding: 12, background: "rgba(255,255,255,0.03)", borderRadius: 12, width: "fit-content" }}>
        {icon}
      </div>
      <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 6 }}>{title}</h3>
      <p style={{ color: "#94a3b8", lineHeight: 1.6, fontSize: 13 }}>{desc}</p>
    </div>
  );
}
