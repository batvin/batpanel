# Batman VPN Panel V2 — Foundation

> V2 is an isolated rebuild. It does not replace or modify the V1 installer, database, certificates, firewall rules, or running services.

## Status

This first milestone establishes the dark dashboard UI and the technical boundary for the multi-protocol backend. The dashboard currently uses clearly labelled demo data. It is not connected to a VPN server and must not be used to provision real users yet.

## Product direction

- Protocol adapters: OpenVPN, Xray (VLESS / VMess / Trojan), and WireGuard.
- Multi-node control plane with per-node health and capability reporting.
- User lifecycle: create, suspend, renew, revoke, quota, expiry and device limits.
- Subscription delivery and client-specific configuration export.
- Telegram bot and documented API.
- Roles, audit events, backup/restore and secure remote-agent communication.
- Dark-first responsive UI with reduced-motion support.

## Architecture rules

1. The control plane must not shell-interpolate user input. Protocol operations belong to typed adapters with validated arguments.
2. A node agent initiates an authenticated outbound connection to the control plane; never expose an unrestricted root SSH endpoint.
3. Store password hashes using Argon2id (or a maintained equivalent), rotate secrets, and never log credentials or private keys.
4. Use TLS, CSRF protection for cookie sessions, secure/HttpOnly/SameSite cookies, rate limits and explicit RBAC.
5. Persist state in a transactional database with schema migrations. Do not use a shared JSON file as the production database.
6. Adapter operations must be idempotent where possible and report capability/health explicitly.
7. V1 data migration must be an explicit, backed-up, reversible operation. No automatic deletion or in-place upgrade.

## Planned milestones

- [x] V2 isolated branch and dark dashboard prototype.
- [ ] Extract and review the V1 embedded application payload; inventory routes, models, dependencies and known defects.
- [ ] Define API contract, database schema and migration tests.
- [ ] Implement authentication, RBAC, audit log and node enrollment.
- [ ] Implement OpenVPN adapter and integration tests.
- [ ] Implement Xray adapter (VLESS, VMess, Trojan) and integration tests.
- [ ] Implement WireGuard adapter and integration tests.
- [ ] Add subscription generation, Telegram integration and reseller roles.
- [ ] Add backup/restore, health monitoring and hardened installer.
- [ ] Test on disposable Ubuntu 22.04/24.04 VMs before any production rollout.

## Run the UI prototype

Open `web/index.html` in a browser. The metrics and node/user records are static demo fixtures.
