// src/AcademicCalendar.jsx
import React from "react";
import { Bot, ArrowLeft, Download } from "lucide-react";
import { Link } from "react-router-dom";
import calendarImg from "./assets/academic-calender.jpg"; // <-- place image here

const NavLink = ({ children, href = "#" }) => (
  <a
    href={href}
    className="px-5 py-2 text-base font-semibold text-zinc-100/90 hover:text-white transition"
  >
    {children}
  </a>
);

export default function AcademicCalendar() {
  return (
    <div className="min-h-screen bg-[#1b1f2a] text-white flex flex-col">
      {/* top accent */}
      <div className="h-1 w-full bg-teal-700/70" />

      {/* header (same look as other pages) */}
      <header className="bg-[#2a2f3a]">
        <div className="w-full max-w-[1600px] mx-auto px-6 lg:px-24">
          <div className="h-16 flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2 font-bold text-xl">
              <div className="grid place-items-center bg-white/10 rounded-lg p-1">
                <Bot className="w-5 h-5" />
              </div>
              <span>UniBot</span>
            </Link>

            <nav className="absolute left-1/2 -translate-x-1/2 hidden md:flex">
              <ul className="flex items-center">
                <li>
                  <NavLink href="/">Home</NavLink>
                </li>
                <li>
                  <NavLink href="/#about">About</NavLink>
                </li>
                <li>
                  <NavLink href="/chat">Ask UniBot</NavLink>
                </li>
                <li>
                  <NavLink href="/#feedback">Feedback</NavLink>
                </li>
              </ul>
            </nav>

            <Link
              to="/chat"
              className="inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold bg-white/10 border border-white/10 hover:bg-white/15"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Chat
            </Link>
          </div>
        </div>
      </header>

      {/* content */}
      <main className="flex-1 w-full max-w-[1200px] mx-auto px-6 lg:px-12 py-8">
        <h1 className="text-3xl font-extrabold text-center mb-6">
          Academic Calendar
        </h1>

        {/* calendar card */}
        <div className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm p-4 lg:p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="text-zinc-300 text-sm">
              United International University · Undergraduate Programs
            </div>
            <a
              href={calendarImg}
              download
              className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold bg-white text-zinc-900 hover:bg-zinc-100"
            >
              <Download className="w-4 h-4" />
              Download
            </a>
          </div>

          {/* image viewer */}
          <div className="rounded-xl overflow-hidden border border-white/10 bg-black/20">
            <img
              src={calendarImg}
              alt="UIU Academic Calendar"
              className="w-full h-auto object-contain"
            />
          </div>

          <p className="mt-4 text-zinc-300 text-sm text-center">
            Official schedule may change—always verify with UIU notices.
          </p>
        </div>
      </main>

      {/* footer */}
      <footer className="bg-[#2a2f3a] py-6">
        <div className="mx-auto max-w-[1200px] px-6 text-center text-zinc-300 text-sm">
          UniBot displays the calendar from official UIU sources.
        </div>
      </footer>
    </div>
  );
}
