#!/usr/bin/env python3
import sys
import traceback

def main():
    try:
        from market_brief_generator import (
            generate_daily_brief_file_only,
            generate_weekly_brief_file_only,
        )
        daily_path = generate_daily_brief_file_only()
        weekly_path = generate_weekly_brief_file_only(force=True)
        print({"daily": daily_path, "weekly": weekly_path})
        return 0
    except Exception as e:
        print("ERROR:", str(e))
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())


