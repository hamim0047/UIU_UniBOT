// src/UniBotLanding.jsx
import React from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Bot,
  ArrowRight,
  Facebook,
  Mail,
  MessageCircle,
  Search,
  CheckCircle2,
  Globe2,
} from "lucide-react";
import heroImg from "./assets/hero.jpg";

/* ---------- tiny UI atoms ---------- */
const NavLink = ({ children, href = "#" }) => (
  <a
    href={href}
    className="px-5 py-2 text-base font-semibold text-zinc-100/90 hover:text-white transition"
  >
    {children}
  </a>
);
const PrimaryButton = ({ children, className = "", ...props }) => (
  <button
    {...props}
    className={`inline-flex items-center gap-2 rounded-full px-6 py-3 text-sm font-extrabold bg-white text-zinc-900 hover:bg-zinc-100 shadow-md transition active:scale-[.98] ${className}`}
  >
    {children}
  </button>
);
const GhostPill = ({ children, className = "", ...props }) => (
  <button
    {...props}
    className={`inline-flex items-center rounded-full px-5 py-2 text-sm font-semibold bg-white/10 text-zinc-100 border border-white/10 hover:border-white/30 hover:bg-white/15 transition ${className}`}
  >
    {children}
  </button>
);
/* accept className so you can size it */
const GradientText = ({ children, className = "" }) => (
  <span
    className={`bg-gradient-to-r from-white via-zinc-200 to-white bg-clip-text text-transparent ${className}`}
  >
    {children}
  </span>
);

/* ---------- cards/steps ---------- */
const FeatureCard = ({ title, desc, icon: Icon }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    transition={{ duration: 0.45 }}
    className="rounded-2xl border border-cyan-300/20 bg-white/5 p-6 shadow-sm"
  >
    <div className="flex items-center gap-3 mb-3">
      <div className="p-2 rounded-xl bg-white/10">
        <Icon className="w-5 h-5 text-white" />
      </div>
      <h3 className="text-white font-semibold">{title}</h3>
    </div>
    <p className="text-zinc-300 text-sm leading-relaxed">{desc}</p>
  </motion.div>
);

const Step = ({ icon: Icon, title, text }) => (
  <div className="flex flex-col items-center text-center">
    <div className="h-20 w-20 rounded-full border-2 border-white/30 grid place-items-center mb-3">
      <Icon className="w-6 h-6" />
    </div>
    <div className="text-white font-semibold">{title}</div>
    <div className="text-zinc-300 text-sm mt-1 max-w-[220px]">{text}</div>
  </div>
);

/* ============================== PAGE ============================== */
export default function UniBotLanding() {
  return (
    <div className="min-h-screen bg-[#1b1f2a] text-white">
      {/* thin top accent bar */}
      <div className="h-1 w-full bg-teal-700/70" />

      {/* header */}
      <header className="sticky top-0 z-40 bg-[#2a2f3a]">
        <div className="mx-auto max-w-8xl px-24">
          <div className="h-16 flex items-center justify-between">
            <a href="/" className="flex items-center gap-2 font-bold text-xl">
              <div className="grid place-items-center bg-white/10 rounded-lg p-1">
                <Bot className="w-5 h-5" />
              </div>
              <span>UniBot</span>
            </a>

            <nav className="absolute left-1/2 -translate-x-1/2 hidden md:flex">
              <ul className="flex items-center">
                <li>
                  <NavLink href="#home">Home</NavLink>
                </li>
                <li>
                  <NavLink href="#about">About</NavLink>
                </li>
                <li>
                  <Link
                    className="px-5 py-2 text-base font-semibold text-zinc-100/90 hover:text-white transition"
                    to="/chat"
                  >
                    Ask UniBot
                  </Link>
                </li>
                <li>
                  <NavLink href="#feedback">Feedback</NavLink>
                </li>
              </ul>
            </nav>

            {/* Get Started goes to chat */}
            <Link to="/chat">
              <GhostPill>Get Started</GhostPill>
            </Link>
          </div>
        </div>
      </header>

      {/* HERO with background image (no robot) */}
      <section
        id="home"
        className="relative bg-cover bg-center"
        style={{ backgroundImage: `url(${heroImg})` }}
      >
        <div className="absolute inset-0 bg-black/40" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/65 via-black/45 to-transparent" />

        <div className="relative mx-auto max-w-8xl px-24 min-h-[70vh] sm:min-h-[80vh] lg:min-h-[88vh] py-16 lg:py-24 grid items-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55 }}
          >
            <h1 className="text-7xl leading-[1.05] font-extrabold tracking-tight">
              Your University, at
              <br />
              <GradientText className="text-8xl">Your Fingertips</GradientText>
            </h1>
            <p className="mt-5 text-3xl text-zinc-100/95">Powered by AI</p>
            <p className="mt-5 text-zinc-200 text-xl max-w-xl">
              UniBot helps you find answers about courses, events, faculty, and
              campus life instantly
            </p>
            <div className="mt-8">
              <Link to="/chat">
                <PrimaryButton>
                  Ask UniBot Now <ArrowRight className="w-4 h-4" />
                </PrimaryButton>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* WHY */}
      <section
        id="about"
        className="py-14 sm:py-16 bg-[radial-gradient(1200px_600px_at_center,#2f3744_0%,#1e2430_60%,#1b1f2a_100%)]"
      >
        <div className="mx-auto max-w-8xl px-24">
          <h2 className="text-center text-4xl sm:text-[34px] font-extrabold mb-10">
            Why Use <GradientText>UniBot?</GradientText>
          </h2>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                t: "Fast Answers",
                d: "Get info in seconds, no searching through websites.",
              },
              {
                t: "Always Up to Date",
                d: "Uses the latest university documents and notices",
              },
              { t: "Bilingual Support", d: "English & Bangla answers" },
              { t: "Available 24/7", d: "Anytime, anywhere" },
            ].map((f, i) => (
              <div
                key={i}
                className="rounded-2xl px-5 py-6 bg-[linear-gradient(180deg,#2d3441,transparent)] border-2 border-cyan-600/45 text-left shadow-[0_1px_0_0_rgba(255,255,255,0.05)_inset]"
              >
                <div className="text-[18px] font-extrabold mb-2">{f.t}</div>
                <p className="text-zinc-300 text-[15px] leading-relaxed">
                  {f.d}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* HOW */}
      <section
        id="ask"
        className="py-14 sm:py-20 bg-[radial-gradient(1200px_700px_at_center,#2c3340_0%,#1e2430_60%,#1b1f2a_100%)]"
      >
        <div className="mx-auto max-w-8xl px-24">
          <h3 className="text-center text-4xl font-extrabold mb-12">
            How <GradientText>UniBot</GradientText> Helps You?
          </h3>

          <div className="flex flex-col items-center gap-8 md:flex-row md:justify-center md:gap-12">
            {["Ask", "Search", "Answer"].map((label, i) => (
              <React.Fragment key={label}>
                <div className="flex flex-col items-center">
                  <div className="h-[110px] w-[110px] rounded-full border-2 border-zinc-400/60 grid place-items-center">
                    <span className="font-extrabold">{label}</span>
                  </div>
                  <p className="mt-4 text-zinc-300 text-xl text-center max-w-[220px]">
                    {label === "Ask" && "Type or speak your question"}
                    {label === "Search" &&
                      "UniBot finds info from official university sources"}
                    {label === "Answer" && "Get a clear, cited response"}
                  </p>
                </div>

                {i < 2 && (
                  <div className="hidden md:block text-white/90 text-5xl -mt-6">
                    →
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>

          {/* Social row */}
          <div className="mt-8 flex justify-center gap-5">
            <a
              aria-label="Facebook"
              href="#"
              className="h-10 w-10 rounded-full grid place-items-center bg-[#1877F2] hover:opacity-90 transition"
            >
              <Facebook className="h-5 w-5 text-white" />
            </a>
            <a
              aria-label="Gmail"
              href="#"
              className="h-10 w-10 rounded-full grid place-items-center bg-white hover:opacity-90 transition"
            >
              <Mail className="h-5 w-5 text-black" />
            </a>
            <a
              aria-label="WhatsApp"
              href="#"
              className="h-10 w-10 rounded-full grid place-items-center bg-[#25D366] hover:opacity-90 transition"
            >
              <MessageCircle className="h-5 w-5 text-white" />
            </a>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-[#2a2f3a] py-6">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p className="text-center text-zinc-300 text-xl">
            UniBot is an AI assistant for United International University and
            provides information based on official sources.
          </p>
        </div>
      </footer>
    </div>
  );
}
