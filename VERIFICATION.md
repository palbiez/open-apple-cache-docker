# Verification and limits

Upstream commit: `68c69e693877f6351b960b755784852f55aa854f`.
Checks dated 2026-11-11. No private runtime logs or site configuration are included.

- Existing Docker deployment: HTTP and HTTPS healthy, running as UID/GID 10001.
- Upstream smoke script inside the container against `http://127.0.0.1:8080`:
  passed, MISS then HIT, 593263 bytes, range bytes 100-199 correct.
- Same upstream smoke script via the LAN gateway: passed with the same bytes.
- SHA256 of that test file:
  `10c77d82b1d1af2690027bfd0cccba5edf8a4dfd1c0ba786836586b8074f11e8`.
- Before these tests, persisted client records showed only earlier synthetic
  downloads, not native Apple-device update traffic. The Mac registration
  helper had not yet been installed in that environment.
- Client tracking behind the gateway collapses clients to its socket address;
  X-Forwarded-For does not change that behavior in the pinned upstream version.
- The helper ZIPs were checked for archive integrity, expected files and
  configuration. The public ZIP contains only source, neutral example and docs.
- Generic standalone Compose: config validation and image build succeeded in
  WSL/Linux Docker. The build reused its verified Go test/vet/build layers.
- Standalone start: init exit 0, HTTP and HTTPS healthy, published host ports
  accessible, generated TLS certificate chain and IP SAN validated.
- Standalone smoke: real Apple file MISS then HIT, correct byte range.
- Helper export produced a valid ZIP using a non-default public download port.
- Restart/reinitialization retained cache ID, master key, setup token and both
  TLS files byte-for-byte. Test containers/network were removed afterwards;
  the running router cache and other services were not restarted.
- Python source syntax and a scan of all publication files plus ZIP entries
  passed. Private .env, runtime auth/keys/registration, personal chat history,
  private issue data and original deployment logs are excluded.

The upstream metric `apple_cache_registered=1` is constant in this revision.
Use the Mac helper's current `status.json` and a real device download to verify
registration/discovery. macOS installation, native discovery, multi-WAN effects,
Mac absence, sustained load and a full router reboot remain unverified here.
