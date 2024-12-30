# Congress Bill Analysis Platform - Database Structure

This document outlines the database structure for the Congress Bill Analysis Platform, which provides AI-generated summaries of congressional bills and amendments from a small government perspective.

## Database Tables

### bills
- `id` (uuid, primary key)
- `congress_number` (integer) - e.g., 117
- `bill_type` (text) - Possible values: "HR", "S", "HJRES", "SJRES", "HCONRES", "SCONRES", "HRES", "SRES"
- `bill_number` (integer) - The assigned bill number
- `title` (text) - Display title of the bill
- `description` (text) - Official bill description
- `origin_chamber` (text) - "House" or "Senate"
- `origin_chamber_code` (text) - "H" or "S"
- `introduced_date` (timestamp)
- `latest_action_date` (timestamp)
- `latest_action_text` (text)
- `update_date` (timestamp) - Last update from Congress.gov
- `constitutional_authority_text` (text) - For House bills only
- `url` (text) - Congress.gov API URL
- `created_at` (timestamp)
- `updated_at` (timestamp)

### amendments
- `id` (uuid, primary key)
- `bill_id` (uuid, foreign key to bills)
- `congress_number` (integer)
- `amendment_type` (text) - "HAMDT", "SAMDT", or "SUAMDT"
- `amendment_number` (integer)
- `description` (text) - For House amendments only
- `purpose` (text) - For House and proposed Senate amendments
- `submitted_date` (timestamp)
- `latest_action_date` (timestamp)
- `latest_action_text` (text)
- `chamber` (text) - "House" or "Senate"
- `url` (text) - Congress.gov API URL
- `created_at` (timestamp)
- `updated_at` (timestamp)

### ai_summaries
- `id` (uuid, primary key)
- `target_id` (uuid) - References either bills.id or amendments.id
- `target_type` (text) - "bill" or "amendment"
- `summary` (text) - AI-generated summary
- `perspective` (text) - Description of the perspective used (e.g., "Milton Friedman small government perspective")
- `key_points` (jsonb) - Array of key points from small government perspective
- `estimated_cost_impact` (text) - Estimated fiscal impact analysis
- `government_growth_analysis` (text) - Analysis of potential government expansion
- `market_impact_analysis` (text) - Analysis of impact on free markets
- `liberty_impact_analysis` (text) - Analysis of impact on individual/economic liberty
- `created_at` (timestamp)
- `updated_at` (timestamp)

### processing_status
- `id` (uuid, primary key)
- `target_id` (uuid) - References either bills.id or amendments.id
- `target_type` (text) - "bill" or "amendment"
- `last_checked` (timestamp)
- `last_processed` (timestamp)
- `status` (text) - "pending", "processing", "completed", "failed"
- `error_message` (text)
- `created_at` (timestamp)
- `updated_at` (timestamp)

## Indexes

### bills
- `idx_bills_congress_number_bill_type_number` (congress_number, bill_type, bill_number)
- `idx_bills_update_date` (update_date)
- `idx_bills_latest_action_date` (latest_action_date)

### amendments
- `idx_amendments_bill_id` (bill_id)
- `idx_amendments_congress_number_type_number` (congress_number, amendment_type, amendment_number)
- `idx_amendments_update_date` (update_date)
- `idx_amendments_latest_action_date` (latest_action_date)

### ai_summaries
- `idx_ai_summaries_target` (target_id, target_type)
- `idx_ai_summaries_created_at` (created_at)

### processing_status
- `idx_processing_status_target` (target_id, target_type)
- `idx_processing_status_status` (status)
- `idx_processing_status_last_checked` (last_checked)

## Notes for Frontend Developers

1. The `bills` and `amendments` tables contain raw data from Congress.gov API, updated daily.

2. The `ai_summaries` table contains our AI-generated analysis from a small government perspective, focusing on:
   - Fiscal impact
   - Government expansion concerns
   - Market freedom implications
   - Individual liberty considerations

3. The `processing_status` table tracks which bills/amendments need analysis or reanalysis.

4. Common queries will include:
   - Latest bills/amendments with completed AI analysis
   - Bills/amendments pending analysis
   - Searching by congress number, bill type, and number
   - Filtering by date ranges
   - Retrieving summaries for specific bills/amendments

5. All timestamps are in UTC.

6. The `key_points` field in `ai_summaries` is a JSONB array for flexible storage of bullet points.

## Example Queries

### Get Latest Analyzed Bills
```sql
SELECT b.*, s.*
FROM bills b
JOIN ai_summaries s ON b.id = s.target_id
WHERE s.target_type = 'bill'
ORDER BY b.latest_action_date DESC
LIMIT 10;
```

### Get Pending Analysis
```sql
SELECT b.*
FROM bills b
LEFT JOIN ai_summaries s ON b.id = s.target_id AND s.target_type = 'bill'
WHERE s.id IS NULL
ORDER BY b.update_date DESC;
```

### Get Bill with Amendments and Summaries
```sql
SELECT b.*, a.*, bs.*, as.*
FROM bills b
LEFT JOIN amendments a ON b.id = a.bill_id
LEFT JOIN ai_summaries bs ON b.id = bs.target_id AND bs.target_type = 'bill'
LEFT JOIN ai_summaries as ON a.id = as.target_id AND as.target_type = 'amendment'
WHERE b.congress_number = 117 AND b.bill_type = 'HR' AND b.bill_number = 3076;
``` 