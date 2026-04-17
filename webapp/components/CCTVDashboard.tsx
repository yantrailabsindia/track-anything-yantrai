"use client";

import React, { useEffect, useState } from "react";
import { fetchCCTVCameras, fetchCCTVLocations, fetchCCTVSnapshots } from "../lib/api";
import { Camera, AlertCircle, Loader, Calendar, Filter } from "lucide-react";

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

interface Snapshot {
  id: string;
  camera_id: string;
  captured_at: string;
  file_path: string;
  url: string;
}

export const CCTVDashboard: React.FC = () => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [locations, setLocations] = useState<Location[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(null);
  const [selectedCameraId, setSelectedCameraId] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split("T")[0]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSnapshot, setSelectedSnapshot] = useState<Snapshot | null>(null);

  // Load cameras and locations
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
        if (camData.length > 0) setSelectedCameraId(camData[0].id);
      } catch (err: any) {
        setError(err.message || "Failed to load CCTV data");
      }
    };

    loadData();
  }, []);

  // Load snapshots for selected camera and date
  useEffect(() => {
    const loadSnapshots = async () => {
      if (!selectedCameraId) return;

      try {
        setLoading(true);
        setError(null);
        const data = await fetchCCTVSnapshots({
          camera_id: selectedCameraId,
          date: selectedDate,
        });
        setSnapshots(data || []);
      } catch (err: any) {
        setError(err.message || "Failed to load snapshots");
        setSnapshots([]);
      } finally {
        setLoading(false);
      }
    };

    loadSnapshots();
  }, [selectedCameraId, selectedDate]);

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
          <span className="text-gradient">CCTV Captured Frames</span>
        </h2>
        {snapshots.length > 0 && (
          <span style={{ fontSize: 12, color: "#64748b", background: "rgba(255,255,255,0.04)", padding: "6px 12px", borderRadius: 8 }}>
            {snapshots.length} frame{snapshots.length !== 1 ? "s" : ""} captured
          </span>
        )}
      </div>

      {/* Filters */}
      <div className="card" style={{ padding: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
          <Filter size={16} color="var(--primary)" />
          <span style={{ fontSize: 14, fontWeight: 600 }}>Filters</span>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
          {/* Location Filter */}
          {locations.length > 0 && (
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 8, color: "#94a3b8" }}>
                Location
              </label>
              <select
                value={selectedLocationId || ""}
                onChange={(e) => {
                  setSelectedLocationId(e.target.value || null);
                  if (filteredCameras.length > 0) setSelectedCameraId(filteredCameras[0].id);
                }}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                  color: "#f0f0f3",
                  fontSize: 13,
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                <option value="">All Locations</option>
                {locations.map((loc) => (
                  <option key={loc.id} value={loc.id}>
                    {loc.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Camera Filter */}
          {filteredCameras.length > 0 && (
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 8, color: "#94a3b8" }}>
                Camera
              </label>
              <select
                value={selectedCameraId || ""}
                onChange={(e) => setSelectedCameraId(e.target.value)}
                style={{
                  width: "100%",
                  padding: "10px 12px",
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: 8,
                  color: "#f0f0f3",
                  fontSize: 13,
                  outline: "none",
                  cursor: "pointer",
                }}
              >
                {filteredCameras.map((cam) => (
                  <option key={cam.id} value={cam.id}>
                    {cam.name}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Date Filter */}
          <div>
            <label style={{ display: "block", fontSize: 12, fontWeight: 600, marginBottom: 8, color: "#94a3b8" }}>
              <Calendar size={14} style={{ display: "inline", marginRight: 6 }} />
              Date
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              style={{
                width: "100%",
                padding: "10px 12px",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 8,
                color: "#f0f0f3",
                fontSize: 13,
                outline: "none",
                cursor: "pointer",
              }}
            />
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div
          style={{
            padding: 16,
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 12,
            display: "flex",
            alignItems: "center",
            gap: 12,
            color: "#fca5a5",
          }}
        >
          <AlertCircle size={18} />
          <span style={{ fontSize: 13 }}>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 40, gap: 12 }}>
          <Loader size={24} color="var(--primary)" style={{ animation: "spin 1s linear infinite" }} />
          <span style={{ color: "#64748b" }}>Loading frames...</span>
        </div>
      )}

      {/* Frames Grid */}
      {!loading && snapshots.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 12 }}>
          {snapshots.map((snapshot) => (
            <div
              key={snapshot.id}
              onClick={() => setSelectedSnapshot(snapshot)}
              style={{
                position: "relative",
                overflow: "hidden",
                borderRadius: 12,
                border: "1px solid rgba(255,255,255,0.1)",
                aspectRatio: "16/9",
                background: "rgba(255,255,255,0.02)",
                cursor: "pointer",
                transition: "all 0.2s",
                transform: "scale(1)",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLElement).style.transform = "scale(1.05)";
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(79,70,229,0.5)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLElement).style.transform = "scale(1)";
                (e.currentTarget as HTMLElement).style.borderColor = "rgba(255,255,255,0.1)";
              }}
            >
              <img src={snapshot.url} alt={`Frame ${snapshot.captured_at}`} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, background: "linear-gradient(to top, rgba(0,0,0,0.6), transparent)", padding: 8 }}>
                <span style={{ fontSize: 11, color: "#cbd5e1", display: "block" }}>
                  {new Date(snapshot.captured_at).toLocaleTimeString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No Frames Message */}
      {!loading && snapshots.length === 0 && (
        <div style={{ padding: 40, textAlign: "center", color: "#475569" }}>
          <Camera size={40} style={{ margin: "0 auto 16px", opacity: 0.3 }} />
          <p style={{ fontSize: 14 }}>No captured frames for this camera on {selectedDate}</p>
          <p style={{ fontSize: 12, color: "#64748b", marginTop: 8 }}>Make sure the CCTV agent is running and cameras are enabled</p>
        </div>
      )}

      {/* Image Viewer Modal */}
      {selectedSnapshot && (
        <div
          onClick={() => setSelectedSnapshot(null)}
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.8)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            cursor: "pointer",
          }}
        >
          <img
            src={selectedSnapshot.url}
            alt="Full frame"
            style={{ maxWidth: "90vw", maxHeight: "90vh", borderRadius: 12, cursor: "auto" }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </div>
  );
};
