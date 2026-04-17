"use client";

import React, { useEffect, useState } from "react";
import { fetchCCTVFeed } from "../lib/api";
import { Camera, Clock, AlertCircle } from "lucide-react";

interface CCTVFeedProps {
  cameraId: string;
  cameraName: string;
  fps?: number;
}

export const CCTVFeed: React.FC<CCTVFeedProps> = ({ cameraId, cameraName, fps = 10 }) => {
  const [imageData, setImageData] = useState<string | null>(null);
  const [capturedAt, setCapturedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  useEffect(() => {
    const fetchLatestFeed = async () => {
      try {
        setError(null);
        const data = await fetchCCTVFeed(cameraId);
        if (data.image_data) {
          setImageData(`data:image/jpeg;base64,${data.image_data}`);
        }
        setCapturedAt(data.captured_at);
        setLastUpdate(new Date());
        setLoading(false);
      } catch (err: any) {
        setError(err.message || "Failed to load feed");
        setLoading(false);
      }
    };

    fetchLatestFeed();

    // Set up auto-refresh based on FPS
    const interval = setInterval(fetchLatestFeed, 1000 / fps);
    return () => clearInterval(interval);
  }, [cameraId, fps]);

  return (
    <div className="card" style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div style={{ padding: "12px 16px", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: loading ? "#fbbf24" : error ? "#f87171" : "#10b981" }} />
          <span style={{ fontWeight: 600, fontSize: 14 }}>{cameraName}</span>
        </div>
        <span style={{ fontSize: 11, color: "#64748b" }}>{fps} FPS</span>
      </div>

      {/* Feed Container */}
      <div style={{ flex: 1, background: "#0f0f12", display: "flex", alignItems: "center", justifyContent: "center", position: "relative", overflow: "hidden" }}>
        {loading && !imageData && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, color: "#64748b" }}>
            <div style={{ width: 32, height: 32, border: "2px solid #4f46e5", borderRadius: "50%", borderTopColor: "transparent", animation: "spin 1s linear infinite" }} />
            <span style={{ fontSize: 12 }}>Loading feed...</span>
          </div>
        )}

        {error && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, color: "#f87171", textAlign: "center" }}>
            <AlertCircle size={32} />
            <span style={{ fontSize: 12 }}>{error}</span>
          </div>
        )}

        {imageData && (
          <img
            src={imageData}
            alt={cameraName}
            style={{ width: "100%", height: "100%", objectFit: "contain" }}
          />
        )}

        {!imageData && !loading && !error && (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, color: "#64748b" }}>
            <Camera size={32} />
            <span style={{ fontSize: 12 }}>No frame available</span>
          </div>
        )}
      </div>

      {/* Footer */}
      {capturedAt && (
        <div style={{ padding: "8px 16px", borderTop: "1px solid rgba(255,255,255,0.05)", fontSize: 11, color: "#94a3b8", display: "flex", alignItems: "center", gap: 6 }}>
          <Clock size={12} />
          {new Date(capturedAt).toLocaleTimeString()}
        </div>
      )}
    </div>
  );
};
