import React, { useState } from "react";

export default function TermsScreen({ onAccept }) {
  const [accepted, setAccepted] = useState(false);

  return (
    <div className="terms-page">
      <div className="terms-card">
        <div className="brand-line">
          <div className="brand-mark small">O</div>
          <strong>Orbit</strong>
        </div>
        <h1>Terms & Conditions</h1>
        <div className="terms-content">
          <p>Before using Orbit, please review and accept the terms for using the workspace and its AI-powered features.</p>
          <p>Orbit may process information that you provide through conversations, documents and workspace files in order to perform requested tasks.</p>
          <p>You remain responsible for reviewing important results before using them in professional or business decisions.</p>
        </div>
        <label className="checkbox-row">
          <input type="checkbox" checked={accepted} onChange={(e) => setAccepted(e.target.checked)} />
          <span>I agree to the Terms & Conditions.</span>
        </label>
        <button className="primary-button" disabled={!accepted} onClick={onAccept}>Accept & Continue</button>
      </div>
    </div>
  );
}