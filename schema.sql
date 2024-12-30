-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create bills table
CREATE TABLE IF NOT EXISTS bills (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    congress_number INTEGER NOT NULL,
    bill_type VARCHAR(10) NOT NULL,
    bill_number INTEGER NOT NULL,
    title TEXT,
    description TEXT,
    origin_chamber VARCHAR(10),
    origin_chamber_code VARCHAR(1),
    introduced_date TIMESTAMP WITH TIME ZONE,
    latest_action_date TIMESTAMP WITH TIME ZONE,
    latest_action_text TEXT,
    update_date TIMESTAMP WITH TIME ZONE,
    constitutional_authority_text TEXT,
    url VARCHAR(500),
    actions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(congress_number, bill_type, bill_number)
);

-- Create amendments table
CREATE TABLE IF NOT EXISTS amendments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    bill_id UUID REFERENCES bills(id) ON DELETE CASCADE,
    congress_number INTEGER NOT NULL,
    amendment_type VARCHAR(10) NOT NULL,
    amendment_number INTEGER NOT NULL,
    description TEXT,
    purpose TEXT,
    submitted_date TIMESTAMP WITH TIME ZONE,
    latest_action_date TIMESTAMP WITH TIME ZONE,
    latest_action_text TEXT,
    chamber VARCHAR(10),
    url VARCHAR(500),
    actions JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(congress_number, amendment_type, amendment_number)
);

-- Create ai_summaries table
CREATE TABLE IF NOT EXISTS ai_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_id UUID NOT NULL,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('bill', 'amendment')),
    summary TEXT NOT NULL,
    analysis TEXT,
    sentiment DECIMAL,
    perspective TEXT,
    key_points JSONB,
    estimated_cost_impact TEXT,
    government_growth_analysis TEXT,
    market_impact_analysis TEXT,
    liberty_impact_analysis TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_id, target_type),
    CONSTRAINT fk_bill_summary
        FOREIGN KEY (target_id)
        REFERENCES bills(id)
        ON DELETE CASCADE
        WHEN (target_type = 'bill'),
    CONSTRAINT fk_amendment_summary
        FOREIGN KEY (target_id)
        REFERENCES amendments(id)
        ON DELETE CASCADE
        WHEN (target_type = 'amendment')
);

-- Create processing_status table
CREATE TABLE IF NOT EXISTS processing_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_id UUID NOT NULL,
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('bill', 'amendment')),
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'processing', 'completed', 'error')),
    error_message TEXT,
    last_processed TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_id, target_type),
    CONSTRAINT fk_bill_status
        FOREIGN KEY (target_id)
        REFERENCES bills(id)
        ON DELETE CASCADE
        WHEN (target_type = 'bill'),
    CONSTRAINT fk_amendment_status
        FOREIGN KEY (target_id)
        REFERENCES amendments(id)
        ON DELETE CASCADE
        WHEN (target_type = 'amendment')
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_bills_congress ON bills(congress_number);
CREATE INDEX IF NOT EXISTS idx_bills_type ON bills(bill_type);
CREATE INDEX IF NOT EXISTS idx_bills_number ON bills(bill_number);
CREATE INDEX IF NOT EXISTS idx_amendments_bill ON amendments(bill_id);
CREATE INDEX IF NOT EXISTS idx_amendments_congress ON amendments(congress_number);
CREATE INDEX IF NOT EXISTS idx_ai_summaries_target ON ai_summaries(target_id, target_type);
CREATE INDEX IF NOT EXISTS idx_processing_status_target ON processing_status(target_id, target_type);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_bills_updated_at
    BEFORE UPDATE ON bills
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_amendments_updated_at
    BEFORE UPDATE ON amendments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_ai_summaries_updated_at
    BEFORE UPDATE ON ai_summaries
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_processing_status_updated_at
    BEFORE UPDATE ON processing_status
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 