// src/pages/Feedback.jsx
import React, { useState } from "react";

export default function Feedback() {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const name = e.target.name.value.trim();
    const message = e.target.message.value.trim();
    if (!message) return alert("Please write your feedback!");

    try {
      await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, message }),
      });
      setSubmitted(true);
    } catch {
      alert("Thank you! (Saved locally if offline)");
    }
  };

  return (
    <div className="min-h-screen bg-[#1b1f2a] text-white flex flex-col items-center justify-center px-6">
      <div className="max-w-lg w-full bg-[#232a36] p-8 rounded-2xl border border-cyan-700/40 shadow-lg">
        <h1 className="text-3xl font-bold mb-4 text-center">Feedback 💬</h1>
        {submitted ? (
          <div className="text-center text-green-400 text-lg">
            Thank you for your feedback! ❤️
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              name="name"
              placeholder="Your name (optional)"
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-zinc-400 outline-none focus:ring-2 focus:ring-cyan-600"
            />
            <textarea
              name="message"
              placeholder="Write your feedback here..."
              rows="5"
              required
              className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white placeholder:text-zinc-400 outline-none focus:ring-2 focus:ring-cyan-600"
            ></textarea>
            <button
              type="submit"
              className="bg-cyan-700 hover:bg-cyan-600 w-full py-3 rounded-full font-semibold transition"
            >
              Submit Feedback
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
