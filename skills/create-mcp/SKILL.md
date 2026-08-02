---
name: create-mcp
description: Expose a self-hosted MCP server (FastMCP/gbrain/etc.) on a permanent, stable HTTPS URL reachable by the claude.ai remote connector, via a named Cloudflare tunnel + OAuth. The proven, standardized MCP-exposure pattern for Tom's fleet (api-bridge, wamexim-brain, collaboo, mz-workouts). Use when adding a new MCP connector, fixing a broken/ephemeral one, or standardizing MCP auth. Captures the hard-won gotchas so you don't re-derive them.
---

# Create / expose an MCP connector (the standardized pattern)

Goal: a self-hosted MCP server reachable from **claude.ai** on a **permanent** HTTPS URL that never churns. Reference implementation: **api-bridge** at `https://bridge.qute.tech` (built 2026-06-28; full battle log in `obsidian-vaults#44`).

## The one constraint that decides everything

**claude.ai's remote connector accepts OAuth 2.1 (authorization-code + PKCE-S256) ONLY.** Static bearer tokens and `?token=` URL creds are NOT accepted for remote connectors (they only work for a *locally-configured stdio* server). So every claude.ai-reachable MCP needs: a public HTTPS URL + an OAuth 2.1 authorization server in front + Dynamic Client Registration (DCR, RFC 7591) or CIMD so Claude self-registers. See `reference_mcp_auth_options` memory + the cited HTML report `agents/quark/artifacts/reports/2026-06-27-mcp-auth-options.html`.

## Architecture (proven)

```
claude.ai  ──HTTPS──>  Cloudflare edge (proxied DNS)  ──named tunnel──>  cloudflared (core)  ──>  127.0.0.1:<port>  (the MCP/FastMCP server, OAuth enforced)
```

- **Domain MUST be a Cloudflare-hosted zone.** A tunnel hostname (`x.example.com` → `<tunnel-id>.cfargotunnel.com`) only resolves when the DNS record is **Proxied (orange-cloud)**, which requires the zone's DNS to live on Cloudflare. An external-DNS CNAME to `cfargotunnel.com` resolves to *nothing* (→ 000). This is why ephemeral `*.trycloudflare.com` "just works" (CF-managed) and a hand-added subdomain doesn't. **CF free does NOT support adding a *subdomain* as a zone — it demands the apex.** So: put a domain (apex) on Cloudflare. If it's an email domain, that's fine — see the email-safety step.
- **Tunnel is dashboard/token-managed** (`run --token`): cloudflared pulls its ingress from Cloudflare ("Updated to new configuration"), **ignoring any local `config.yml` ingress**. Configure public hostnames via the API or dashboard, not the yaml.
- **Run as systemd `--user` services** (linger on) so a reboot can't break it. Never leave it as `nohup` processes.

## Prerequisites (one-time per account)

1. A domain on Cloudflare (apex). Tom's MCP domain = **qute.tech** (email-only Google Workspace domain, migrated to CF 2026-06-28). Zone id in `/tmp`/issue #44.
2. A scoped Cloudflare API token at `~/.config/cloudflare.env` (`CLOUDFLARE_API_TOKEN=…`), with **BOTH**: `Zone:DNS:Edit` (on the MCP zone) **and** `Account:Cloudflare Tunnel:Edit`. (Editing a token to add the 2nd permission can silently drop the 1st — verify both rows survive.)
3. A Cloudflare **named tunnel** (created in Zero Trust). Tom's = `14096fae-…` (token embedded in `~/.config/systemd/user/cloudflared-mcp-tunnel.service`).

### Migrating an email domain onto Cloudflare safely (verify-before-flip)

When the apex domain also runs email (Google Workspace MX), the ONLY risk is the nameserver change. De-risk it:
1. `dig MX <domain> @1.1.1.1` + `dig TXT …` (+ `_dmarc`, `google._domainkey`) → record what must survive.
2. Cloudflare → Add a domain (apex) → Free. It scans + imports records. **Confirm all MX + TXT imported (DNS-only/grey for MX) BEFORE touching nameservers.**
3. Only then switch nameservers at the registrar to Cloudflare's. Email keeps flowing (same MX, served by CF). Verify post-flip: `dig MX <domain> @<cf-nameserver>`.

## Steps to expose one MCP (`<name>.<domain>` → `127.0.0.1:<port>`)

All via the scoped token; helper vars: `source ~/.config/cloudflare.env`, `ACCT=<account-id>`, `TID=<tunnel-id>`, `ZID=<zone-id>`.

1. **Tunnel ingress** — add the hostname → local service (PUT the full ingress array; keep the catch-all 404 last):
   ```
   curl -s -X PUT "https://api.cloudflare.com/client/v4/accounts/$ACCT/cfd_tunnel/$TID/configurations" \
     -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H 'Content-Type: application/json' \
     -d '{"config":{"ingress":[{"hostname":"<name>.<domain>","service":"http://localhost:<port>"}, … , {"service":"http_status:404"}]}}'
   ```
2. **Proxied DNS** — CNAME to the tunnel:
   ```
   curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZID/dns_records" \
     -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" -H 'Content-Type: application/json' \
     -d '{"type":"CNAME","name":"<name>.<domain>","content":"'$TID'.cfargotunnel.com","proxied":true,"ttl":1}'
   ```
3. **Point the MCP server at the URL** — set its public-URL env (e.g. `API_BRIDGE_PUBLIC_URL=https://<name>.<domain>` in `~/.config/api-bridge.env`) and **restart the server** (OAuth metadata is baked at startup).
4. **Ensure the tunnel + server run as systemd --user services** (see template below). `systemctl --user` needs the bus env: `export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`.
5. **Test BEFORE trusting** (the step that catches everything):
   ```
   curl -s -o/dev/null -w '%{http_code}\n' -X POST https://<name>.<domain>/mcp -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1}'   # → 401
   curl -s https://<name>.<domain>/.well-known/oauth-protected-resource    # resource/AS must show <name>.<domain>
   curl -s https://<name>.<domain>/.well-known/oauth-authorization-server  # issuer + registration_endpoint present (DCR)
   ```
6. **GitHub OAuth App callback** (if the server uses GitHubProvider auth): set the app's Authorization callback URL to **exactly** `https://<name>.<domain>/auth/callback` (no trailing slash). The client_id is in the server env.
7. **Add the connector in claude.ai**: custom connector → `https://<name>.<domain>/mcp`. Watch the server log for the flow: `POST /register 201 → GET /authorize 302 → GET /auth/callback?code=… 302 → POST /token 200 → POST /mcp 200`.

## systemd --user templates (durable, no sudo; linger must be on)

Files in `~/.config/systemd/user/`, then `daemon-reload; enable --now`. See the live `api-bridge-mcp.service` + `cloudflared-mcp-tunnel.service`.

```ini
# cloudflared-mcp-tunnel.service
[Unit]
Description=cloudflared named tunnel — MCP endpoints
After=network-online.target
Wants=network-online.target
[Service]
ExecStart=/home/tom/.local/bin/cloudflared tunnel --config <cfg> --no-autoupdate run --token <TOKEN>
Restart=always
RestartSec=5
[Install]
WantedBy=default.target
```

## Failure modes (each cost time — recognise fast)

- **`brain.example.com` → 000 / public DNS returns the cfargotunnel CNAME but no address** → the domain isn't a CF zone, OR the DNS record is grey-cloud. Fix: zone on CF + record Proxied.
- **GitHub: "The redirect_uri is not associated with this application"** → the GitHub OAuth App's callback URL ≠ `https://<name>.<domain>/auth/callback`. Update it. (This was the last blocker on api-bridge.)
- **`IdP callback missing code or transaction ID` (proxy.py)** → either the redirect_uri mismatch above (no code issued), or the server **restarted mid-flow** (OAuth transactions are in-memory) — don't restart while testing; retry fresh.
- **`Authentication error` on a CF API call** → token scope wrong/missing. Verify BOTH `Zone:DNS:Edit` + `Account:Tunnel:Edit` (adding one can drop the other).
- **`systemctl --user`: "Failed to connect to bus: No medium found"** → set `XDG_RUNTIME_DIR=/run/user/1000` + `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`.
- **FastMCP defaults that break claude.ai** (fix in the server, see `api-bridge-mcp/CONNECTOR-SETUP.md`): `enable_cimd=False` (its CIMD offer is malformed → forces clean DCR), `require_authorization_consent=False` (else /authorize stops at an HTML approve page), and serve the RFC 9728 PRM doc at the **origin-root** `/.well-known/oauth-protected-resource` (claude.ai probes root, FastMCP defaults to the `/mcp`-suffixed path only).
- **Ephemeral TryCloudflare URL churns on every restart** → that's the anti-pattern this skill replaces. Use a named tunnel on a CF zone.

## References

- Live reference impl: `api-bridge-mcp/CONNECTOR-SETUP.md` (FastMCP GitHubProvider + the 3 claude.ai-compat fixes), `api-bridge-mcp/scripts/run-http.sh`.
- Build log + decisions: `obsidian-vaults#44`; standardization epic `obsidian-vaults#45` (item 1 = standardize MCP exposure).
- Auth landscape: `agents/quark/artifacts/reports/2026-06-27-mcp-auth-options.html`; memories `reference_mcp_auth_options`, `reference_api_bridge_mcp_public_endpoint`.
- gbrain/wamexim-brain is the other live pattern (built-in OAuth 2.1 + scopes on `:8300`); migrate it to `brain.qute.tech` with these same steps.
