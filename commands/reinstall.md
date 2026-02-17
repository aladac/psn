---
description: Reinstall PSN plugin via Homebrew with latest source
allowed-tools: ["Bash"]
---

# Reinstall PSN

Reinstall the psn CLI tool via Homebrew with the latest source from GitHub.

## Steps

### 1. Push latest psn source to GitHub (if needed)

Check for uncommitted changes in psn source and push:
```bash
cd /Users/chi/Projects/psn && git status --short
```

If changes exist, commit and push them:
```bash
cd /Users/chi/Projects/psn && git add -A && git commit -m "Update $(date +%Y-%m-%d)" && git push
```

### 2. Update Homebrew tap

```bash
cd /opt/homebrew/Library/Taps/saiden-dev/homebrew-tap && git fetch origin && git reset --hard origin/main
```

### 3. Uninstall current psn

```bash
brew uninstall psn 2>/dev/null || true
rm -f /opt/homebrew/bin/psn
```

### 4. Install latest HEAD

```bash
HOMEBREW_NO_INSTALL_CLEANUP=1 brew install --HEAD saiden-dev/tap/psn
```

### 5. Verify installation

```bash
/opt/homebrew/bin/psn --version && /opt/homebrew/bin/psn --help | head -10
```

## Expected Warning

A dylib relinking warning for cryptography is **expected and harmless**:
```
Error: Failed changing dylib ID of .../cryptography/hazmat/bindings/_rust.abi3.so
```

The cryptography package uses a Rust binary with insufficient mach-o header space for Homebrew's relinking. This does not affect functionality.

## Success Criteria

- `psn --version` returns version info
- `psn --help` shows available commands
- Binary exists at `/opt/homebrew/bin/psn`
