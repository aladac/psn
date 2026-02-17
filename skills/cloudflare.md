---
description: 'Use this skill when working with Cloudflare DNS, Tunnels, Pages, or Workers. Triggers on questions about DNS records, tunnel management, static site deployment, or serverless workers.'
---

# Tools Reference

## Built-in Tools
| Tool | Purpose |
|------|---------|
| `Bash` | Execute flarectl, cloudflared, wrangler commands |
| `Read` | Read config files (wrangler.toml, config.yml) |
| `Write` | Create/update config files |
| `Edit` | Modify existing configs |

## Related Commands (psn:cf:*)
| Command | Purpose |
|---------|---------|
| `/cf:list_zones` | List all zones |
| `/cf:zone_info` | Zone details |
| `/cf:add_host` | Add DNS record |
| `/cf:del_host` | Delete DNS record |
| `/cf:list_tunnels` | List tunnels |
| `/cf:add_tunnel` | Create tunnel |
| `/cf:del_tunnel` | Delete tunnel |
| `/cf:tunnel_info` | Tunnel details |
| `/cf:pages_list` | List Pages projects |
| `/cf:pages_deploy` | Deploy to Pages |
| `/cf:pages_destroy` | Delete project |
| `/cf:workers_list` | List Workers |
| `/cf:worker_info` | Worker details |
| `/cf:worker` | Worker operations |

## Related Agents
- `psn:hostmaster` - Cloudflare infrastructure agent

---

# Cloudflare Operations

Comprehensive guide for Cloudflare infrastructure management.

## Prerequisites

- `wrangler` CLI installed and authenticated
- Cloudflare API token with appropriate permissions
- For tunnels: `cloudflared` installed

## DNS Management

### Record Types
| Type | Purpose | Example |
|------|---------|---------|
| A | IPv4 address | `192.168.1.1` |
| AAAA | IPv6 address | `2001:db8::1` |
| CNAME | Alias to another domain | `www` → `example.com` |
| TXT | Text record (SPF, DKIM, verification) | `v=spf1 include:...` |
| MX | Mail server | `mail.example.com` (priority 10) |

### Adding Records
```bash
# A record with proxy
/cf:add_host example.com A www 192.168.1.1 true

# CNAME record
/cf:add_host example.com CNAME blog myblog.pages.dev false

# TXT record (verification)
/cf:add_host example.com TXT @ "google-site-verification=..."
```

### Deleting Records
```bash
/cf:del_host example.com www
```

### Proxy vs DNS-only
- **Proxied (orange cloud)**: Traffic flows through Cloudflare CDN, gets DDoS protection, caching, SSL
- **DNS-only (gray cloud)**: Direct connection, no Cloudflare features

## Tunnel Management

Cloudflare Tunnels expose local services without opening ports.

### Create Tunnel
```bash
/cf:add_tunnel my-tunnel
```

### Configure Tunnel
Edit `~/.cloudflared/config.yml`:
```yaml
tunnel: <tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: app.example.com
    service: http://localhost:8080
  - hostname: api.example.com
    service: http://localhost:3000
  - service: http_status:404
```

### Route DNS
```bash
cloudflared tunnel route dns my-tunnel app.example.com
```

### List Tunnels
```bash
/cf:list_tunnels
```

### Tunnel Info
```bash
/cf:tunnel_info my-tunnel
```

### Delete Tunnel
```bash
/cf:del_tunnel my-tunnel
```

## Pages Deployment

Deploy static sites to Cloudflare Pages.

### Deploy
```bash
# Deploy build output
/cf:pages_deploy ./dist my-site main

# Production deployment
/cf:pages_deploy ./build production-site main
```

### List Projects
```bash
/cf:pages_list
```

### Delete Project
```bash
/cf:pages_destroy my-old-site
```

### Build Configuration
For framework-specific builds, use `wrangler.toml`:
```toml
name = "my-site"
pages_build_output_dir = "./dist"

[build]
command = "npm run build"
```

### Custom Domains
After deployment:
1. Go to Pages dashboard
2. Custom domains → Add
3. Add DNS record (automatic if zone is on Cloudflare)

## Workers

Serverless functions at the edge.

### Actions
```bash
# Initialize new worker
/cf:worker init my-worker

# Run locally
/cf:worker dev my-worker

# Deploy to production
/cf:worker deploy my-worker

# View logs
/cf:worker tail my-worker

# Delete worker
/cf:worker delete my-worker
```

### List Workers
```bash
/cf:workers_list
```

### Worker Info
```bash
/cf:worker_info my-worker
```

### Worker Structure
```
my-worker/
├── wrangler.toml
├── src/
│   └── index.ts
├── package.json
└── tsconfig.json
```

### Basic Worker
```typescript
// src/index.ts
export default {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/api/hello') {
      return new Response(JSON.stringify({ message: 'Hello!' }), {
        headers: { 'Content-Type': 'application/json' }
      });
    }

    return new Response('Not found', { status: 404 });
  }
};
```

### wrangler.toml
```toml
name = "my-worker"
main = "src/index.ts"
compatibility_date = "2024-01-01"

[vars]
ENVIRONMENT = "production"

[[kv_namespaces]]
binding = "MY_KV"
id = "xxx"
```

## Zone Management

### List Zones
```bash
/cf:list_zones
```

### Zone Info
```bash
/cf:zone_info example.com
```

Returns:
- Zone ID
- Status (active, pending, etc.)
- Name servers
- Plan level

## Common Workflows

### Expose Local Service
```bash
# 1. Create tunnel
/cf:add_tunnel my-app

# 2. Configure ingress (edit config.yml)

# 3. Route DNS
cloudflared tunnel route dns my-app app.example.com

# 4. Run tunnel
cloudflared tunnel run my-app
```

### Deploy Static Site
```bash
# 1. Build site
npm run build

# 2. Deploy
/cf:pages_deploy ./dist my-site main

# 3. (Optional) Add custom domain via dashboard
```

### Deploy API Worker
```bash
# 1. Init
/cf:worker init my-api

# 2. Develop locally
/cf:worker dev my-api

# 3. Deploy
/cf:worker deploy my-api

# 4. Add route (via dashboard or wrangler.toml)
```

## Troubleshooting

### Tunnel not connecting
- Check `cloudflared` is running
- Verify credentials file exists
- Check tunnel status: `/cf:tunnel_info <name>`

### Pages build failing
- Check build command in dashboard
- Verify build output directory
- Check environment variables

### Worker errors
- Tail logs: `/cf:worker tail <name>`
- Check wrangler.toml syntax
- Verify KV/D1 bindings

### DNS not propagating
- Check TTL settings
- Verify proxy status (orange vs gray cloud)
- Wait for propagation (up to 48h for some changes)
