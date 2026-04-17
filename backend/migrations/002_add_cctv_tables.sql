-- CCTV Agent Tables Migration
-- Created: 2026-04-13

-- Camera Locations Table
CREATE TABLE IF NOT EXISTS camera_locations (
    id VARCHAR NOT NULL PRIMARY KEY,
    org_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    address VARCHAR,
    latitude VARCHAR,
    longitude VARCHAR,
    timezone VARCHAR DEFAULT 'UTC',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(org_id) REFERENCES organizations(id),
    INDEX ix_camera_location_org (org_id)
);

-- Cameras Table
CREATE TABLE IF NOT EXISTS cameras (
    id VARCHAR NOT NULL PRIMARY KEY,
    location_id VARCHAR NOT NULL,
    org_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    ip_address VARCHAR NOT NULL,
    onvif_port INTEGER DEFAULT 80,
    rtsp_url VARCHAR,
    manufacturer VARCHAR,
    model VARCHAR,
    hardware_id VARCHAR,
    firmware_version VARCHAR,
    snapshot_interval_seconds INTEGER DEFAULT 300,
    jpeg_quality INTEGER DEFAULT 85,
    resolution_profile VARCHAR DEFAULT 'sub',
    status VARCHAR DEFAULT 'offline',
    last_seen_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(location_id) REFERENCES camera_locations(id),
    FOREIGN KEY(org_id) REFERENCES organizations(id),
    INDEX ix_camera_org_location (org_id, location_id)
);

-- CCTV Snapshots Table
CREATE TABLE IF NOT EXISTS cctv_snapshots (
    id INTEGER NOT NULL PRIMARY KEY AUTO_INCREMENT,
    camera_id VARCHAR NOT NULL,
    location_id VARCHAR NOT NULL,
    org_id VARCHAR NOT NULL,
    captured_at TIMESTAMP NOT NULL,
    hour_bucket INTEGER NOT NULL,
    date_bucket VARCHAR(10) NOT NULL,
    gcs_path VARCHAR NOT NULL,
    gcs_url VARCHAR,
    file_size_bytes INTEGER,
    resolution VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(camera_id) REFERENCES cameras(id),
    FOREIGN KEY(location_id) REFERENCES camera_locations(id),
    FOREIGN KEY(org_id) REFERENCES organizations(id),
    INDEX ix_snapshot_org_location_camera_date_hour (org_id, location_id, camera_id, date_bucket, hour_bucket),
    INDEX ix_snapshot_org_timestamp (org_id, captured_at),
    INDEX ix_snapshot_captured_at (captured_at)
);

-- CCTV Agent Registrations Table
CREATE TABLE IF NOT EXISTS cctv_agent_registrations (
    id VARCHAR NOT NULL PRIMARY KEY,
    org_id VARCHAR NOT NULL,
    agent_name VARCHAR NOT NULL,
    api_key VARCHAR NOT NULL UNIQUE,
    location_id VARCHAR,
    status VARCHAR DEFAULT 'offline',
    last_heartbeat_at TIMESTAMP,
    config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(org_id) REFERENCES organizations(id),
    FOREIGN KEY(location_id) REFERENCES camera_locations(id),
    INDEX ix_agent_org (org_id),
    INDEX ix_agent_api_key (api_key)
);
