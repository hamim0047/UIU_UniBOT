import React from "react";
import { Routes, Route, Link } from "react-router-dom";
import Landing from "./UniBotLandingPage.jsx";
import Chat from "./Chat.jsx";
import Feedback from "./Feedback.jsx";
import AcademicCalender from "./AcademicCalender.jsx";
import CampusMap from "./CampusMap.jsx"; 


function NotFound() {
  return (
    <div className="min-h-screen grid place-items-center text-center p-8 text-white bg-zinc-900">
      <div>
        <h1 className="text-3xl font-bold mb-2">404</h1>
        <p className="mb-4 text-zinc-300">Page not found</p>
        <Link className="underline" to="/">
          Go home
        </Link>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/chat" element={<Chat />} />
      <Route path="/calendar" element={<AcademicCalender />} />
      <Route path="/map" element={<CampusMap />} />
      <Route path="/feedback" element={<Feedback />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
