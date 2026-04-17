"use client";

import React, { useEffect, useState } from "react";
import { fetchCCTVCameras, fetchCCTVLocations } from "../lib/api";
import { CCTVFeed } from "./CCTVFeed";
import { Camera, AlertCircle, Loader } from "lucide-react";

interface Camera {
  id: string;
  name: string;
  location_id: string;
  frame_rate_fps: number;
  status: string;
}

interface Location {
  id: string;
  name: string;
}

export const CCTVDashboard: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        setError(null);
        const [locData, camData] = await Promise.all([
          fetchCCTVLocations().catch(() => []),
          fetchCCTVCameras(),
        ]);
        setLocations(locData);
        setCameras(camData);
        if (locData.length > 0) setSelectedLocationId(locData[0].id);
        setLoading(false);
      } catch (err: any) {
        setError(err.message || "Failed to load CCTV cameras");
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const filteredCameras = selectedLocationId
    ? cameras.filter((cam) => cam.location_id === selectedLocationId)
    : cameras;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ fontSize: 24, fontWeight: 800, display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ background: "rgba(79,70,229,0.15)", padding: 10, borderRadius: 12 }}>
            <Camera size={20} color="var(--primary)" />
          </div>
          <span className="text-gradient">Live CCTV Feeds</span>
        </h2>
        {cameras.length > 0 && (
          <span style={{ fontSize: 12, color: "#64748b", background: "rgba(255,255,255,0.04)", padding: "6px 12px", borderRadius: 8 }}>
            {filteredCameras.length} camera{filteredCameras.length !== 1 ? "s" : ""} online
          </span>
        )}
      </div>

      {/* Location Filter */}
      {locations.length > 1 && (
        <div style={{ display: "flex", gap: 8, overflowX: "auto", paddingBottom: 8 }}>
          <button
            onClick={() => setSelectedLocationId(null)}
            style={{
              padding: "8px 16px",
              borderRadius: 8,
              border: selectedLocationId === null ? "2px solid var(--primary)" : "1px solid rgba(255,255,255,0.1)",
              background: selectedLocationId === null ? "rgba(79,70,229,0.15)" : "rgba(255,255,255,0.04)",
              color: selectedLocationId === null ? "var(--primary)" : "#94a3b8",
              fontSize: 12,
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s",
              whiteSpace: "nowrap",
            }}
          >
            All Locations
          </button>
          {locations.map((loc) => (
            <button
              key={loc.id}
              onClick={() => setSelectedLocationId(loc.id)}
              style={{
                padding: "8px 16px",
                borderRadius: 8,
                border: selectedLocationId === loc.id ? "2px solid var(--primary)" : "1px solid rgba(255,255,255,0.1)",
                background: selectedLocationId === loc.id ? "rgba(79,70,229,0.15)" : "rgba(255,255,255,0.04)",
                color: selectedLocationId === loc.id ? "var(--primary)" : "#94a3b8",
                fontSize: 12,
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s",
                whiteSpace: "nowrap",
              }}
            >
              {loc.name}
            </button>
          ))}
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 300, color: "#64748b" }}>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
            <Loader size={32} style={{ animation: "spin 1s linear infinite" }} />
            <span style={{ fontSize: 14 }}>Loading CCTV feeds...</span>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 300 }} className="card">
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, color: "#f87171", textAlign: "center" }}>
            <AlertCircle size={32} />
            <span style={{ fontSize: 14, fontWeight: 600 }}>Unable to load CCTV feeds</span>
            <span style={{ fontSize: 12, color: "#94a3b8" }}>{error}</span>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredCameras.length === 0 && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: 300 }} className="card">
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, color: "#64748b", textAlign: "center" }}>
            <Camera size={32} />
            <span style={{ fontSize: 14, fontWeight: 600 }}>No cameras found</span>
            <span style={{ fontSize: 12 }}>Set up CCTV cameras in settings to view live feeds.</span>
          </div>
        </div>
      )}

      {/* Camera Grid */}
      {!loading && !error && filteredCameras.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))",
            gap: 16,
          }}
        >
          {filteredCameras.map((camera) => (
            <div key={camera.id} style={{ minHeight: 300 }}>
              <CCTVFeed
                cameraId={camera.id}
                cameraName={camera.name}
                fps={camera.frame_rate_fps || 10}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
