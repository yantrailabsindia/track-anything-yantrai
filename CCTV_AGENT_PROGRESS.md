# CCTV Agent Implementation Progress

**Status**: Phase 1-2 Complete, Phase 3-5 In Progress

## ✅ COMPLETED

### Backend (Phase 1)
- [x] Database models: CameraLocation, Camera, CCTVSnapshot, CCTVAgentRegistration
- [x] CCTV API router: 10 endpoints (agent/register, heartbeat, locations, cameras, snapshots)
- [x] GCS service: signed URL generation, upload, delete, metadata
- [x] Migration SQL: 4 new tables with indexes

### Agent Core (Phase 2a)
- [x] `cctv_agent/config.py` - configuration constants
- [x] `cctv_agent/core/onvif_client.py` - ONVIF protocol (copied from streamer)
- [x] `cctv_agent/core/credential_store.py` - DPAPI credential storage
- [x] `cctv_agent/core/config_manager.py` - JSON config + camera management

### Agent Services (Phase 2b)
- [x] `cctv_agent/services/frame_grabber.py` - single-frame RTSP capture with retry
- [x] `cctv_agent/services/gcs_uploader.py` - GCS upload wrapper
- [x] `cctv_agent/services/db_manager.py` - SQLite queue + status tracking

### Agent Workers (Phase 2c) - PARTIAL
- [x] `cctv_agent/workers/log_emitter.py` - JSONL log file writer

## ⏳ TODO

### Agent Workers (Phase 2c) - REMAINING
- [ ] `cctv_agent/workers/snapshot_worker.py` - periodic frame capture per camera
- [ ] `cctv_agent/workers/upload_worker.py` - hourly/on-demand batch upload
- [ ] `cctv_agent/workers/heartbeat_worker.py` - 30s heartbeat + telemetry
- [ ] `cctv_agent/workers/discovery_worker.py` - periodic ONVIF re-scan

### Agent Entry Points (Phase 2d)
- [ ] `cctv_agent/main_service.py` - headless service main loop
- [ ] `cctv_agent/main_gui.py` - GUI launcher (starts service + GUI)

### Agent GUI (Phase 2e) - 5 Tabs
- [ ] `cctv_agent/ui/main_window.py` - tabbed interface
- [ ] `cctv_agent/ui/discovery_tab.py` - scan + add cameras
- [ ] `cctv_agent/ui/cameras_tab.py` - camera list + settings
- [ ] `cctv_agent/ui/cloud_config_tab.py` - GCS + backend config
- [ ] `cctv_agent/ui/capture_logs_tab.py` - live log viewer (last 10 events)
- [ ] `cctv_agent/ui/queue_status_tab.py` - queue summary + Refresh/Upload buttons
- [ ] `cctv_agent/ui/status_tab.py` - overall health

### Build & Test (Phase 3)
- [ ] `cctv_agent/build.spec` - PyInstaller config → CCTVAgent.exe
- [ ] Integration tests: end-to-end verification

## Architecture Summary

```
CCTVAgent.exe (two-process):
├─ GUI Process (PySide6)
│  ├─ 5 tabs (discovery, cameras, cloud config, logs, queue status, status)
│  ├─ Reads shared SQLite DB
│  ├─ Touches FORCE_UPLOAD signal file
│  └─ Tail-reads logs.jsonl
└─ Headless Service Process (background)
   ├─ Snapshot Capture Worker (per camera, on interval)
   ├─ Upload Worker (hourly + on-demand)
   ├─ Heartbeat Worker (every 30s)
   ├─ Discovery Worker (every 10m)
   └─ Log Emitter (writes all events)
```

## Key Files Status

| File | Status | Notes |
|------|--------|-------|
| `backend/models.py` | ✅ | 4 CCTV models added |
| `backend/routers/cctv.py` | ✅ | 10 endpoints |
| `backend/services/gcs_service.py` | ✅ | Signed URLs |
| `cctv_agent/config.py` | ✅ | Defaults + env vars |
| `cctv_agent/core/*` | ✅ | ONVIF, credentials, config |
| `cctv_agent/services/*` | ✅ | Frame grabber, GCS, SQLite |
| `cctv_agent/workers/log_emitter.py` | ✅ | JSONL logger |
| `cctv_agent/workers/snapshot_worker.py` | 🔨 | NEEDS CODING |
| `cctv_agent/workers/upload_worker.py` | 🔨 | NEEDS CODING |
| `cctv_agent/workers/heartbeat_worker.py` | 🔨 | NEEDS CODING |
| `cctv_agent/workers/discovery_worker.py` | 🔨 | NEEDS CODING |
| `cctv_agent/main_service.py` | 🔨 | NEEDS CODING |
| `cctv_agent/main_gui.py` | 🔨 | NEEDS CODING |
| `cctv_agent/ui/*` | 🔨 | NEEDS CODING (7 files) |
| `cctv_agent/build.spec` | 🔨 | NEEDS CODING |

## Next Steps

1. Complete snapshot_worker.py, upload_worker.py, heartbeat_worker.py, discovery_worker.py
2. Create main_service.py with thread orchestration
3. Create GUI entry point and all 5 tabs
4. Configure PyInstaller build
5. Integration testing

**Estimated remaining**: 8-10 files, ~2000 lines of code
