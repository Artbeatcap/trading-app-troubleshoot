ALTER TABLE "user" ADD COLUMN IF NOT EXISTS default_risk_percent double precision DEFAULT 2.0;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS account_size double precision;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS display_name varchar(64);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS dark_mode boolean DEFAULT false;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS daily_brief_email boolean DEFAULT true;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS timezone varchar(64) DEFAULT 'UTC';
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS api_key varchar(64);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS email_verified boolean DEFAULT false;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS email_verification_token varchar(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS token_generated_at timestamp without time zone;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_reset_token varchar(100);
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_reset_token_generated_at timestamp without time zone;


