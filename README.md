# reddit-realestates-scraper

Scrapes Bay Area subreddit posts (housing, real estate, local topics) into CSV.

## Quick start
```bash
python3 scrape_reddit.py                                   # new posts from default Bay Area subs
python3 scrape_reddit.py --sort top --time month           # top posts this month
python3 scrape_reddit.py --query "rent OR mortgage OR housing" --limit 300
```
Output goes to `data/bayarea_reddit_<date>.csv` (gitignored). Stdlib only, no installs needed.

Default subreddits: bayarea, BayAreaRealEstate, sanfrancisco, SanJose, oakland, berkeley, PaloAlto, southbaybayarea.

## Running from the cloud (Reddit API credentials)
Reddit blocks anonymous requests from cloud/datacenter IPs. To run in Claude Code on the web:
1. Create a **script** app at https://www.reddit.com/prefs/apps (redirect URI can be `http://localhost`).
2. Add `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` as environment variables in the cloud environment settings.
3. Allow `www.reddit.com` and `oauth.reddit.com` in the environment's network access.

With those set, the script automatically uses the official API at `oauth.reddit.com`.

## Claude Code setup
- `.claude/skills/web-scraper-extractor/` — vendored from
  [Sharan0516/claude-skill-web-scraper](https://github.com/Sharan0516/claude-skill-web-scraper) (browser-based scraping skill).
- `.mcp.json` — Playwright MCP, headless, using the Chromium preinstalled in Claude Code cloud containers.
