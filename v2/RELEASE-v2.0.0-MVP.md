# BAT-PANEL V2.0.0 MVP — Release Candidate Notes

**Release channel:** MVP / controlled evaluation  
**Supported platform:** Ubuntu 22.04 or 24.04, amd64  
**Scope:** Single-host control-plane dashboard

## What this build provides

- Persian RTL dashboard served by FastAPI
- Administrator login and authenticated management API
- Persistent SQLite records for customers and nodes
- Dashboard summary and protocol labels
- Docker Compose deployment with health check and container hardening
- `bat-panel` operator menu, service lifecycle, logs, backups, update, port and admin credential management
- Installer preserves the existing V2 environment and backs up the V2 data volume before updating

## Explicit exclusions (not implemented)

This is **not** a production VPN subscription panel yet. Customer creation stores a management record only. It does not provision or revoke VPN accounts.

- No live OpenVPN, Xray (VLESS/VMess/Trojan), or WireGuard provisioning
- No real traffic metering or quota/expiry enforcement
- No enforcement-based suspension, live connection status, or generated client configuration
- No node agent, Telegram bot, reseller workflow, or V1 migration

Do not sell access or promise VPN service delivery based on this MVP.

## Network and security

The default Compose bind is `127.0.0.1:8000`. This is intentional. Do not expose the API/dashboard as plain HTTP on a public interface. Use an SSH tunnel for controlled access, or configure a domain-backed HTTPS reverse proxy with access controls and a firewall allowlist. Never share `.env`, admin credentials, tokens, or unredacted logs.

SSH tunnel example (run on the administrator's own computer):

```bash
ssh -N -L 8000:127.0.0.1:8000 root@SERVER_IP
```

Open `http://127.0.0.1:8000` locally while the tunnel is active.

## Fresh installation

Review the repository's `v2/DEPLOYMENT.md` first. Then run on a supported clean host:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/batvin/batpanel/main/install-v2.sh)
```

The installer requests administrator credentials interactively. Store them securely.

## Operator verification

```bash
bat-panel
docker compose -p batman-v2 -f /opt/batman-v2/docker-compose.yml --env-file /opt/batman-v2/.env ps
curl -fsS http://127.0.0.1:8000/api/health
```

Confirm the API reports `ok: true`, container health is healthy, login succeeds, and a test record remains after container restart. Make and verify a backup before any update.

## Release gate before public production use

A production designation requires independent testing of:
1. Authentication/session expiry, brute-force protection and authorization boundaries
2. HTTPS deployment, CSRF/CORS/security headers and secrets handling
3. Database migration, restore drills and interrupted-update recovery
4. Actual provisioning/revocation and quota/expiry enforcement for each supported VPN engine
5. Automated integration tests on a disposable Ubuntu VM
6. Resource/load tests and a documented upgrade/rollback path

These gates have not been certified by this MVP release note.
