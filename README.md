# Turku EnergiaOnline – Home Assistant integration

Unofficial, experimental integration for electricity consumption history from the EnergiaOnline internal API. Not affiliated with Turku Energia or Fingrid.

**Privacy:** This public repository contains no personal identifiers, HAR captures, passwords, tokens, customer numbers, metering-point identifiers, addresses or measured consumption. Enter your own details only in Home Assistant.

**Limitations:** The observed API supports a daily (`P1D`) consumption response. Quarter-hour resolution (`PT15M`) is experimental and unverified. The undocumented API and subscription-key-only authentication may change or reject unattended access. This integration is not suitable for real-time/safety-critical applications.

## Installation with HACS

1. In HACS, add `https://github.com/artepe/turku-energia-haos` as a custom **Integration** repository.
2. Install **Turku EnergiaOnline (Unofficial)** and restart Home Assistant.
3. Settings → Devices & services → Add integration → **Turku EnergiaOnline**.
4. Add credentials and identifiers *locally*. Never post these into GitHub issues.

## Readings and statistics

The integration provides the latest interval, available readings today and in the current month, plus a separate energy-history statistic for the Energy Dashboard. Source data may be delayed 6–24 hours. Only complete 15-minute hours are aggregated; missing readings are not converted into zero. For the daily-only fallback, daily usage is assigned to the day's last local hour; this does **not** represent real hourly usage. Backfilled corrections to already imported statistics are not yet handled.

Do not add this grid-import statistic to Energy Dashboard if another meter already counts the same grid consumption, or you will double-count.

This is a proof-of-concept beta intended for testing only. See source files and tests for implementation details.

MIT License.
