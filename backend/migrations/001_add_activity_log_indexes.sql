-- Add indexes to activity_logs for improved query performance
-- These indexes optimize the aggregator queries in get_logs_for_date()

-- Index on user_id alone (for employee queries)
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id
ON activity_logs(user_id);

-- Composite index: user_id + timestamp (common filter combination)
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id_timestamp
ON activity_logs(user_id, timestamp);

-- Composite index: org_id + timestamp + user_id (org-scoped, user-specific queries)
CREATE INDEX IF NOT EXISTS idx_activity_logs_org_id_timestamp_user_id
ON activity_logs(org_id, timestamp, user_id);

-- Composite index: device_id + timestamp (device activity queries)
CREATE INDEX IF NOT EXISTS idx_activity_logs_device_id_timestamp
ON activity_logs(device_id, timestamp);

-- Composite index: org_id + user_id (organization scope + user filter)
CREATE INDEX IF NOT EXISTS idx_activity_logs_org_id_user_id
ON activity_logs(org_id, user_id);
