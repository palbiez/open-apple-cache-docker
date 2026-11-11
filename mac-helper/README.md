# macOS registration helper

Apple's locator accepts the Linux cache only after a registration signed by a
private macOS AuthKit implementation. This helper keeps that operation on a Mac
and refreshes the Linux cache registration every 3,000 seconds.

The helper sends the configured cache GUID, local address, local range, cache
capabilities and a locally generated 32-byte placeholder push token to Apple's
`lcdn/session` and `lcdn/register` endpoints. The placeholder cannot receive APNS
notifications because third-party binaries do not have Apple's private
AssetCache entitlement. Periodic registration is therefore the recovery and
renewal mechanism.

`native-registration.m` resolves the installed AuthKit signing function from the
current method implementation instead of embedding an address. A macOS update
may still change the private interface. Every run has strict timeouts, a
single-instance lock and an atomic `status.json`; launchd retries failed runs at
the next interval.

The installed directory must contain:

- `native-registration`, compiled from `native-registration.m`;
- `register_once.py` and `registration.json`;
- Apple's public `cert.cer`, downloaded automatically on first run.

The launch agent runs as the logged-in user and stores session material only in
memory. `registration.json` must omit `session-token`; it is inserted from the
matching live session immediately before signing.
