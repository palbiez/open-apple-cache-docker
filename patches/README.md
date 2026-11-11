# Origin Cache-Control policy patch

`0001-ignore-origin-cache-control.patch` applies to upstream commit
`68c69e693877f6351b960b755784852f55aa854f`. The Docker build checks and applies
the patch before running the Go tests, vet and compilation.

This distribution always ignores the origin response's Cache-Control for
storage decisions, including private, no-cache, no-store, max-age and s-maxage.
No filename-specific exception, opt-in setting or directive allowlist is used.
The configured `max_ttl_seconds` defines local retention from receipt; origin
Age, Date and Expires do not shorten it. Original response headers are still
forwarded to the client and retained with cached objects.

The same rule applies during ETag/size validation for a new signed Apple URL.
That validation still requires a strong matching ETag and complete object size.
It never aliases a changed representation just because its path matches.

Other existing rules remain active: origin/client allowlists, authorization and
cookie rejection, Set-Cookie/Vary/encoding response guards, request no-store,
range validation, complete-transfer checks, capacity, local expiry and size
limits. This is an intentional application policy change from upstream's
ordinary HTTP-cache behavior. Apple cache-session/range/result headers remain.

Tests cover arbitrary origin Cache-Control values, stale origin freshness
headers, full/partial transfers, signed URL changes, restart persistence and
rejection of changed ETags or sizes. The patched image logs the selected policy
and local retention on startup.

Upstream source is MIT licensed; see the upstream LICENSE and repository notice.
