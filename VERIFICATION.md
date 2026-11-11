# Verification and limits

Checks dated 2026-11-11. Base upstream commit:
`68c69e693877f6351b960b755784852f55aa854f`, with
`patches/0001-ignore-origin-cache-control.patch`.
No private runtime logs, signed URLs or site configuration are included.

## Go policy and image build

- `go test -race -count=1 ./...` and `go vet ./...`: passed against the patched
  source, including the existing upstream tests.
- Added tests cover private/no-cache/no-store, combined, absent and malformed
  origin Cache-Control, local retention independent of Age/Date/Expires,
  forwarding original headers, full/partial Apple packages, signed URL changes
  and persistence after restart. Changed ETags or sizes are rejected for reuse.
- Linux/amd64 Docker build: patch applicability check, application, Go tests,
  vet and compilation all passed. Only allowlisted files enter the build context.
- The startup JSON log reports `origin_cache_control: ignored` and the local
  retention. The runtime image has patchset label `ignore-origin-cache-control-v1`.

## Patched image with isolated state

- Separate config/data, no published host ports, UID/GID 10001, read-only root
  and dropped capabilities: healthy.
- Upstream smoke script against `http://127.0.0.1:8080`: passed, MISS then HIT,
  593263 bytes, correct range 100-199. File SHA256:
  `10c77d82b1d1af2690027bfd0cccba5edf8a4dfd1c0ba786836586b8074f11e8`.
- Actual Apple app package with origin `Cache-Control: private`: first MISS,
  then HIT, 153247 bytes, correct HIT range 100-199. File SHA256:
  `946a263cfd8172acf2de494d23d5e1dcb8fed9eba620e509b50574bc9c6719c9`.
- Original private directive and Apple cache-session/range headers remained.
- After a container restart the private package was still HIT. Cache ID,
  master key and setup token were retained. The test container was removed.

## Existing deployment upgrade

- Patched image deployed with a new local tag after a metadata/config backup.
  Cache health, UID/GID 10001 and read-only root verified.
- Config, TLS, accounts, cache ID, master key and setup token matched the backup.
  Unrelated running container IDs were unchanged during the upgrade.
- Existing HTTPS administrator login accessible with certificate validation.
- The same private Apple app was stored on its initial request through the LAN
  gateway and served as HIT on subsequent full and partial requests.
- This checks the real origin through the gateway using controlled HTTP
  requests. A repeated native-device app update after the patch remains to be
  observed separately; this test does not establish that result.

## Docker integration and helper checks

Earlier checks of the integration passed: standalone Compose config/build,
init exit 0, HTTP/HTTPS health, published ports, generated TLS IP SAN,
MISS/HIT/range smoke, and restart/reinitialization preserving identity/TLS.
The Go patch does not modify the Compose or helper integration.

The public helper ZIP passed archive integrity and source/configuration checks.
It includes the German guide and neutral example. Publication scans exclude
private .env, auth/keys/registration, chat history, issue data and deployment logs.

Native Mac discovery and Mac/iPad app requests were observed before the policy
patch. Their private origin responses caused BYPASS in the original binary.
After the patch, repeated native-device HIT, renewal with the Mac absent,
sustained load and a full router reboot remain unverified.

The upstream `apple_cache_registered=1` metric is constant in this revision.
Use fresh helper status, the native locator and actual downloads to assess
registration/discovery. Behind a gateway, client tracking uses its socket
address; X-Forwarded-For does not expand that into separate devices.
