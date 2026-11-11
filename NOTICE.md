# Source provenance

Docker integration for [Mau2rice0/Open-Apple-Cache](https://github.com/Mau2rice0/Open-Apple-Cache).
The Dockerfile fetches commit `68c69e693877f6351b960b755784852f55aa854f`.
It then applies `patches/0001-ignore-origin-cache-control.patch`; the running
service therefore includes that local behavior change rather than being an
unmodified upstream binary. See the patch README for the exact storage policy.
The upstream helper files under `mac-helper/` are copied from that commit;
`configure.py` and `ANLEITUNG.md` are additions for this distribution.
See `LICENSE.upstream` and `mac-helper/LICENSE.upstream` for the upstream MIT notice.
No Apple proprietary binary, certificate, private key, device identity, session
token, user configuration or private deployment log is bundled.
