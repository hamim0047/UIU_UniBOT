// src/CampusMap.jsx
import React from "react";
import { Link } from "react-router-dom";
import { Bot, ArrowLeft, MapPin } from "lucide-react";

export default function CampusMap() {
  const embedUrl =
    "https://www.google.com/maps?q=United+International+University,+Madani+Avenue,+Dhaka+1212&output=embed";
  const mapsLink =
    "https://www.google.com/maps/place/United+International+University,+Madani+Avenue,+Dhaka+1212";

  return (
    <div className="relative h-screen w-screen bg-black">
      {/* Fullscreen Google Map */}
      <iframe
        title="UIU Location"
        src={embedUrl}
        className="absolute inset-0 h-full w-full border-0"
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        allowFullScreen
      />

      {/* Top-left overlay panel */}
      <div className="absolute top-4 left-4 right-4 sm:right-auto z-10">
        <div className="max-w-md rounded-2xl border border-white/15 bg-black/55 backdrop-blur-md text-white shadow-lg">
          {/* Title bar */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
            <div className="flex items-center gap-2 font-bold">
              <div className="grid place-items-center bg-white/10 rounded-lg p-1">
                <Bot className="w-5 h-5" />
              </div>
              <span>UniBot</span>
            </div>

            <Link
              to="/chat"
              className="inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold bg-white/10 border border-white/10 hover:bg-white/20 transition"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Chat
            </Link>
          </div>

          {/* Content */}
          <div className="px-4 py-4">
            <div className="flex items-center gap-2 font-semibold">
              <MapPin className="w-5 h-5" />
              <span>Campus Location</span>
            </div>

            <p className="mt-3 text-zinc-200 text-sm leading-relaxed">
              <span className="font-semibold">
                United International University (UIU)
              </span>
              <br />
              Madani Avenue, Satarkul, Badda, Dhaka 1212, Bangladesh
            </p>

            <a
              href={mapsLink}
              target="_blank"
              rel="noreferrer"
              className="mt-4 inline-flex items-center justify-center rounded-lg px-4 py-2 bg-white text-zinc-900 font-semibold hover:bg-zinc-100 transition"
            >
              Open in Google Maps
            </a>

            <p className="mt-3 text-xs text-zinc-300">
              Tip: Zoom and pan the map. The panel stays on top.
            </p>
          </div>
        </div>
      </div>

      {/* Optional: small brand chip bottom-left */}
      <div className="absolute bottom-4 left-4 z-10">
        <div className="rounded-full px-3 py-1 text-xs font-semibold text-white/90 bg-black/50 backdrop-blur-md border border-white/10">
          UIU • Dhaka 1212
        </div>
      </div>
    </div>
  );
}
