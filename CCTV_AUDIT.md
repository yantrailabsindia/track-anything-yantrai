# CCTV Agent to Webapp Pipeline Audit

## Overview
End-to-end audit of the CCTV agent → backend → webapp flow. Identifies what's working, gaps, and issues.

---

## PIPELINE STEPS

### Step 1: Agent Download & Credential Setup ✅
**Location:** Agent downloaded from webapp → User runs `.exe` on Windows

**How it works:**
1. User creates account on webapp with username/password
2. User downloads CCTV agent `.exe` from `/download` page
3. Runs agent on Windows machine
4. Agent starts and opens GUI (PySide6 window)

**Files involved:**
- `main.py` - Entry point
- `core/config_manager.py` - Stores config in `~/CCTVViewer/config.json`

**Current behavior:**
- `api_url` and `api_key` must be manually set in Cloud Tab settings
- User must have account on webapp + obtain API key from somewhere
- **GAP:** No login UI to enter webapp credentials in agent
- **GAP:** API key generation not clearly documented

**Issues:**
- ❌ User can't directly log in with webapp credentials
- ❌ No clear flow to obtain/set API key
- ❌ Agent ID is hardcoded as "site-01"

---

### Step 2: Network Scanning for CCTV Devices ✅
**Location:** Discovery Tab → "Rescan Network"

**How it works:**
1. User clicks "Rescan Network" button
2. Starts `ONVIFScanner` (QThread) which:
   - Broadcasts ONVIF discovery messages
   - Scans ONVIF port 8080
   - Returns list of devices (IP, Manufacturer, Model, Type)
3. Results displayed in table

**Files involved:**
- `ui/discovery_tab.py` - UI for discovery
- `core/onvif_scanner.py` - ONVIF scanning logic

**Current behavior:**
- Shows found devices in table
- User can double-click to authenticate or right-click for context menu

**Issues:**
- ✅ Works well for ONVIF devices
- ⚠️ Only finds ONVIF-enabled devices (some old DVRs don't support ONVIF)

---

### Step 3: Adding RTSP Credentials ✅
**Location:** Discovery Tab → Double-click device → Auth Dialog

**How it works:**
1. User double-clicks a discovered device
2. `AuthDialog` opens with:
   - Username field
   - Password field
3. User enters RTSP credentials
4. Dialog verifies connection (tries ONVIF login)
5. On success, device is added to viewer

**Files involved:**
- `ui/auth_dialog.py` - Credential input dialog
- `ui/viewer_tab.py` - Adds device to tree

**Current behavior:**
- Credentials are tested against the device
- Device info stored in config with RTSP URL
- Multiple channels detected from device

**Issues:**
- ✅ Works well
- ⚠️ Only stores one credential set per device (username/password)

---

### Step 4: Frame Capture & Push ✅
**Location:** `core/snapshot_worker.py` + `core/stream_worker.py`

**How it works:**
1. User clicks checkbox to enable camera in viewer
2. `StreamWorker` starts capturing from RTSP stream using OpenCV
3. Each frame is converted to QImage
4. Frame emitted via signal: `frame_captured.emit(qimage, camera_id)`
5. `SnapshotWorker` receives frame:
   - Converts QImage → JPEG bytes
   - Encodes to base64
   - POSTs to `/api/cctv/snapshots` with:
     ```json
     {
       "camera_id": "cam1",
       "captured_at": "2026-04-17T14:30:45.123456",
       "username": "agent_id",
       "image_data": "base64_jpeg_string"
     }
     ```
6. Backend receives and stores locally

**Files involved:**
- `core/snapshot_worker.py` - Captures and pushes frames
- `core/stream_worker.py` - RTSP capture + frame emitter
- `ui/viewer_tab.py` - Connects signals

**Storage format:**
```
~/CCTVViewer/data/cctv/{username}/{YYYYMMDD}/
{CAMERA_ID}_{YYYYMMDD}_{HHMMSS}_{mmm}.jpg

Example:
~/CCTVViewer/data/cctv/agent_id/20260417/
FRONT_GATE_20260417_143025_123.jpg
```

**Frame rate control:**
- Default: 10 FPS (100ms interval)
- Set in `config.json` → `snapshot.frame_rate_fps`
- Currently hardcoded options: 5, 10, 30 FPS

**Issues:**
- ✅ Capture and push working
- ⚠️ FPS is global for all cameras (not per-camera from agent UI)
- ❌ No UI in agent to select which cameras to capture
- ❌ No UI in agent to adjust FPS per camera

---

### Step 5: Backend Receives & Stores ✅
**Location:** `/api/cctv/snapshots` POST endpoint

**How it works:**
1. Backend receives POST with base64 image data
2. Verifies agent API key
3. Decodes base64 → JPEG bytes
4. Creates folder: `data/cctv/{username}/{YYYYMMDD}/`
5. Saves file: `{CAMERA_ID}_{YYYYMMDD}_{HHMMSS}_{mmm}.jpg`
6. Stores metadata in `cctv_snapshots` table:
   - `camera_id`
   - `org_id`
   - `location_id`
   - `captured_at`
   - `hour_bucket` (0-23)
   - `date_bucket` (YYYY-MM-DD)
   - `gcs_path` (local file path)
   - `file_size_bytes`

**Files involved:**
- `backend/routers/cctv.py` - POST /api/cctv/snapshots endpoint
- `backend/models.py` - CCTVSnapshot model

**Issues:**
- ✅ Working correctly
- ⚠️ Column `gcs_path` is confusing (stores local path, not GCS)

---

### Step 6: Viewing in Webapp ❌ WRONG IMPLEMENTATION
**Current (WRONG):** Live feed with auto-refresh
**Wanted:** Stored frames table view like logs/screenshots page

#### Current Wrong Implementation:
- `webapp/components/CCTVFeed.tsx` - Auto-refreshes every 1000/fps ms
- `webapp/components/CCTVDashboard.tsx` - Grid layout with live feeds
- `/api/cctv/feed/{camera_id}` endpoint returns latest snapshot as base64
- Creates "streaming" effect by constantly fetching latest frame

**Issues with current approach:**
- ❌ Not what user wants (live streaming, not stored archive)
- ❌ Inefficient constant polling
- ❌ Similar to screenshot view - should show table of stored frames
- ❌ No ability to browse historical frames by date/time
- ❌ No UI to filter by camera, location, date

---

### Step 7: Frame Rate Configuration (NEEDS FIXING) ❌
**Current issues:**
1. **Agent side:**
   - No UI in agent to set FPS
   - No UI in agent to select which cameras to capture
   - Only config.json can be manually edited

2. **Webapp side (I built, but DISABLE per user request):**
   - FPS settings in Settings page (lines 175-222 of settings/page.tsx)
   - Accessible to all users (employees, team leads, admins)
   - **USER WANTS THIS DISABLED**
   - Should only be in agent, not in webapp

**Desired flow:**
1. User opens agent GUI
2. Goes to "CCTV Settings" tab
3. Sees list of detected cameras with checkboxes
4. Can enable/disable capture per camera
5. Can set FPS per camera (1, 5, 10, 15, 20, 24 FPS)
6. Settings saved to config.json
7. SnapshotWorker respects per-camera settings

---

## ISSUES & GAPS SUMMARY

### Critical Issues:
1. **❌ Agent has no UI for camera selection**
   - Must manually edit config.json
   - Should be in GUI with checkboxes

2. **❌ Agent has no UI for FPS configuration**
   - Must manually edit config.json
   - Should be in GUI per camera

3. **❌ Webapp shows live feed (wrong)**
   - Should show stored frames like logs/screenshots
   - Should show table with date/time/camera filters
   - Should allow browsing historical frames

4. **❌ FPS settings in webapp settings page**
   - User wants this DISABLED
   - Control should be in agent only

### Design Issues:
1. **Agent login flow**
   - No clear way to obtain API key
   - Should prompt for webapp credentials on first run
   - Should handle agent registration automatically

2. **Frame rate control**
   - Currently global (all cameras same FPS)
   - Should be per-camera
   - Should respect agent UI settings, not webapp settings

3. **Data visibility**
   - Webapp should show STORED frames in table format
   - Similar to how logs page shows screenshots
   - With filters: date, camera, location

---

## WHAT'S WORKING ✅

| Component | Status | Notes |
|-----------|--------|-------|
| Agent startup | ✅ | Fixed infinite window bug |
| Network scanning | ✅ | ONVIF discovery working |
| Credential input | ✅ | AuthDialog working |
| Frame capture | ✅ | SnapshotWorker capturing frames |
| Backend storage | ✅ | Storing in local filesystem |
| Database metadata | ✅ | cctv_snapshots table tracking |
| API endpoints | ✅ | /cctv/snapshots, /cctv/feed working |

---

## WHAT NEEDS FIXING ❌

| Component | Issue | Priority |
|-----------|-------|----------|
| Agent UI - Camera selection | No UI to enable/disable cameras | HIGH |
| Agent UI - FPS control | No UI to set FPS per camera | HIGH |
| Webapp view - Frame display | Live feed instead of stored archive | HIGH |
| Webapp UI - FPS settings | Should be disabled/removed | HIGH |
| Agent login | No automatic registration | MEDIUM |
| Webapp - Frame history | No date/time filtering | MEDIUM |
| Agent config | FPS is global, not per-camera | MEDIUM |

---

## RECOMMENDED CHANGES

### 1. Agent Side - Add "CCTV Settings" Tab
```
Main Window Tabs:
- Discovery ✅
- Live Viewer ✅
- ☁ Cloud ✅
- CCTV Settings ← NEW

CCTV Settings Tab should show:
┌─────────────────────────────────────────┐
│ Enabled Cameras:                        │
│ ☑ Front Gate (5 FPS)                    │
│ ☑ Lobby (10 FPS)                        │
│ ☐ Back Entrance (disabled)              │
│ ☑ Parking Lot (30 FPS)                  │
│                                         │
│ Add Camera | Remove | Save Settings     │
└─────────────────────────────────────────┘
```

### 2. Disable FPS Settings in Webapp
- Remove CCTV Camera Settings section from `/settings`
- Remove FPS selector UI (lines 175-222 in settings/page.tsx)
- Keep camera listing but don't allow FPS changes

### 3. Change Webapp View from Live Feed to Stored Archive
**New `/logs` page CCTV tab:**
```
Filters:
- Date picker (YYYY-MM-DD)
- Camera selector
- Location selector

Results Table:
| Time        | Camera      | Location | Action  |
|-------------|------------|----------|---------|
| 14:30:45    | Front Gate | Lobby    | View    |
| 14:30:15    | Lobby      | Lobby    | View    |
| 14:29:50    | Back Ent.  | Parking  | View    |

Click "View" → Show image in modal like screenshot view
```

---

## CREDENTIALS & AUTHENTICATION FLOW

### Current State:
1. User manually enters `api_url` and `api_key` in agent Cloud Tab
2. No clear source for API key
3. Agent ID hardcoded as "site-01"

### Desired State:
1. Agent starts → Prompts for login
2. User enters webapp username/password
3. Agent automatically:
   - Registers itself via `/api/cctv/agent/register`
   - Receives `api_key`
   - Stores in config.json
   - No manual setup needed

---

## DATABASE SCHEMA NOTES

**Current cctv_snapshots table:**
```
id (int, PK)
camera_id (str, FK)
location_id (str, FK)
org_id (str, FK)
captured_at (datetime)
hour_bucket (int, 0-23)
date_bucket (str, YYYY-MM-DD)
gcs_path (str) ← Misleading name, stores local path
gcs_url (str, nullable)
file_size_bytes (int)
resolution (str, e.g. "1920x1080")
created_at (datetime)
```

**Indexes:**
- (org_id, location_id, camera_id, date_bucket, hour_bucket)
- (org_id, captured_at)

**Notes:**
- Column `gcs_path` should be renamed to `file_path` for clarity
- All metadata correctly captured for filtering/querying

---

## FINAL ASSESSMENT

### What's Done ✅
- Infinite window bug fixed
- Frame capture & push implemented
- Backend storage implemented
- Database schema ready

### What's Wrong ❌
- Agent has no UI for camera/FPS selection
- Webapp shows live feed (wrong approach)
- FPS settings in webapp should be disabled
- No stored frame archive view

### Next Steps (in order):
1. Add "CCTV Settings" tab to agent
2. Disable FPS settings in webapp settings page
3. Replace live feed view with stored frames table
4. Add date/camera/location filters to frame table

---

**Audit Date:** 2026-04-17
**Auditor:** Claude
**Status:** REQUIRES CHANGES - Core pipeline works but UI/UX needs adjustments
