# Options Plunge Market Brief Makefile

.PHONY: help brief-dry brief-send weekly-dry weekly-send social-twitter install-deps test admin-pro admin-free admin-status

help:
	@echo "Options Plunge Market Brief Commands:"
	@echo "  make brief-dry     - Generate daily brief email files without sending (dry run)"
	@echo "  make brief-send    - Send daily brief to subscribers (requires CONFIRM_SEND=1)"
	@echo "  make weekly-dry    - Generate weekly brief email files without sending (dry run)"
	@echo "  make weekly-send   - Send weekly brief to subscribers (requires CONFIRM_SEND=1)"
	@echo "  make social-twitter - Generate Twitter CSV from brief data"
	@echo "  make install-deps  - Install required dependencies"
	@echo "  make test          - Test the market brief system"
	@echo "  make admin-pro     - Upgrade admin user to Pro status"
	@echo "  make admin-free    - Downgrade admin user to free status"
	@echo "  make admin-status  - Show admin user status"
	@echo "  make migrate-briefs - Create market briefs database table"
	@echo "  make populate-samples - Create sample historical briefs"
	@echo "  make test-briefs   - Test complete brief system"

install-deps:
	@echo "Installing dependencies..."
	pip install pydantic jinja2 apscheduler pytz

brief-dry:
	@echo "Running daily brief dry run..."
	python send_morning_brief.py daily_brief_sample.json --dry-run

brief-send:
	@echo "Sending daily brief to subscribers..."
	@if [ "$(CONFIRM_SEND)" != "1" ]; then \
		echo "Error: CONFIRM_SEND=1 environment variable required"; \
		echo "Set CONFIRM_SEND=1 to confirm you want to send to all subscribers"; \
		exit 1; \
	fi
	python send_morning_brief.py daily_brief_sample.json

weekly-dry:
	@echo "Running weekly brief dry run..."
	python send_weekly_brief.py --source weekly_brief_sample.json --dry-run

weekly-send:
	@echo "Sending weekly brief to subscribers..."
	@if [ "$(CONFIRM_SEND)" != "1" ]; then \
		echo "Error: CONFIRM_SEND=1 environment variable required"; \
		echo "Set CONFIRM_SEND=1 to confirm you want to send to all subscribers"; \
		exit 1; \
	fi
	python send_weekly_brief.py --source weekly_brief_sample.json

social-twitter:
	@echo "Generating Twitter CSV..."
	python generate_twitter_csv.py daily_brief_sample.json

test:
	@echo "Testing market brief system..."
	@echo "1. Testing daily brief dry run..."
	make brief-dry
	@echo "2. Testing weekly brief dry run..."
	make weekly-dry
	@echo "3. Testing Twitter CSV generation..."
	make social-twitter
	@echo "✓ All tests completed successfully"

# Development helpers
clean:
	@echo "Cleaning output directories..."
	rm -rf out/

validate-json:
	@echo "Validating daily brief JSON..."
	python -c "from daily_brief_schema import MorningBrief; import json; MorningBrief(**json.load(open('daily_brief_sample.json'))); print('✓ Daily brief JSON is valid')"

validate-weekly-json:
	@echo "Validating weekly brief JSON..."
	python -c "from weekly_brief_schema import WeeklyBrief; import json; WeeklyBrief(**json.load(open('weekly_brief_sample.json'))); print('✓ Weekly brief JSON is valid')"

migrate-db:
	@echo "Running database migration..."
	python migrate_weekly_subscription.py

admin-pro:
	@echo "Upgrading admin to Pro status..."
	python upgrade_admin_to_pro.py upgrade

admin-free:
	@echo "Downgrading admin to free status..."
	python upgrade_admin_to_pro.py downgrade

admin-status:
	@echo "Showing admin status..."
	python upgrade_admin_to_pro.py status

# Market Brief Management
migrate-briefs:
	@echo "Creating market briefs table..."
	python migrate_market_briefs_table.py

populate-samples:
	@echo "Creating sample market briefs..."
	python populate_sample_briefs.py

test-briefs:
	@echo "Testing market brief system..."
	@echo "1. Testing weekly brief dry run..."
	make weekly-dry
	@echo "2. Testing brief storage..."
	python populate_sample_briefs.py
	@echo "✓ Market brief system test completed"

