# Cloudflare Authentication Configuration

## MANDATORY Environment Variables

**USE ONLY THESE THREE VARIABLES. NO EXCEPTIONS.**

| Variable | Value |
|----------|-------|
| `CLOUDFLARE_API_KEY` | Global API Key |
| `CLOUDFLARE_EMAIL` | Account email |
| `CLOUDFLARE_ACCOUNT_ID` | `95ad3baa2a4ecda1e38342df7d24204f` |

## FORBIDDEN Variables

**NEVER SET OR USE:**

- `CF_API_KEY`
- `CF_API_EMAIL`
- `CF_EMAIL`
- `CF_ACCOUNT_ID`
- `CF_API_TOKEN`
- `CLOUDFLARE_API_TOKEN`
- Any variable containing `TOKEN`

## Shell Configuration

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Cloudflare Authentication - ONLY these three variables
export CLOUDFLARE_API_KEY="your-global-api-key"
export CLOUDFLARE_EMAIL="your-email@example.com"
export CLOUDFLARE_ACCOUNT_ID="95ad3baa2a4ecda1e38342df7d24204f"
```

## Tools

Both `wrangler` and `flarectl` support Global API Key authentication via `CLOUDFLARE_API_KEY` + `CLOUDFLARE_EMAIL`.

## References

- [Wrangler System Environment Variables](https://developers.cloudflare.com/workers/wrangler/system-environment-variables/)
