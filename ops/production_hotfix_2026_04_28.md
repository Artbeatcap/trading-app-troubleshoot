# Production Hotfix: Twitter Market Data and SendGrid Secrets

Applied on the production VPS on 2026-04-28.

## Twitter Post Market Data

The deployed `twitter_auto_emailer.py` was the source of the 5 PM ET `Post-Market Twitter Post` email. Its legacy Tradier fetch returned missing SPY/QQQ/VIX data and the generator formatted those missing values as `$0.00`/`0.00`.

Production was patched to:

- load SPY, QQQ, IWM, and VIX from the app's shared `market_brief_generator.fetch_stock_prices()` provider;
- call the shared market-data validation before generating or sending Twitter email copy;
- fall back to Tradier only when it returns positive required prices;
- abort before sending if SPY, QQQ, or VIX are unavailable.

The post-market systemd timer remains `twitter-postmarket.timer`, which runs `twitter_auto_emailer.py --time postmarket`.

## SendGrid Secret Handling

Active SendGrid keys were moved out of app-owned and systemd plaintext config files.

Production now loads SendGrid credentials from root-owned files:

- `/etc/optionsplunge/sendgrid.env`
- `/etc/optionsplunge/stock-news-sendgrid.env`

Both files are owned by `root:root` and use `0600` permissions. The keys were not rotated during this hotfix.

Affected services were reloaded/restarted so they read SendGrid credentials from the restricted env files:

- `trading-analysis`
- `market-brief-scheduler`
- `weekly-brief-scheduler`
- `newsletter-scheduler`
- `twitter-premarket`
- `twitter-postmarket`
- legacy `/root/stock-news-email` Docker Compose agent

Verification confirmed no SendGrid key literals remained outside the restricted root-owned secret files.
