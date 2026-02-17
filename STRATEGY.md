# Build & Agent Strategy

Guidelines for optimizing development workflow through background tasks and parallel agent execution.

## Background Task Strategy

### When to Run in Background

| Task | Background? | Reason |
|------|-------------|--------|
| `cargo build --release` | Yes | 2-15 min, can plan/review meanwhile |
| `bundle install` | Yes | 30s-5min, especially with native gems |
| `npm/pnpm install` | Yes | 30s-3min on fresh installs |
| `dx build --release` | Yes | 2-5 min for WASM builds |
| `pip install` / `uv sync` | Maybe | Fast with uv, slow with pip |
| Full test suites | Yes | Run while implementing next feature |
| `cargo clippy` on large codebase | Yes | Can take 1-2 min |

### When to Run Foreground

| Task | Foreground? | Reason |
|------|-------------|--------|
| `cargo check` | Yes | Fast (5-30s), need immediate feedback |
| Single test file | Yes | Quick validation cycle |
| `dx serve` | Yes | Interactive, need hot reload feedback |
| Git operations | Yes | Fast, need status confirmation |
| File reads/edits | Yes | Instantaneous |
| `cargo fmt` / linting | Yes | Sub-second, blocking is fine |

### Background Task Patterns

```bash
# Start build in background, continue working
Task(run_in_background=true, prompt="Run cargo build --release")

# Check on it later
Read("/tmp/claude-501/.../tasks/<id>.output")
# or
Bash("tail -20 /tmp/claude-501/.../tasks/<id>.output")
```

**Rule of thumb:** If it takes >30 seconds and you don't need the output immediately, background it.

## Parallel Agent Strategy

### When to Use Parallel Agents

**Good candidates for parallelization:**

1. **Independent research tasks**
   ```
   Task(subagent_type="Explore", prompt="Find all authentication code")
   Task(subagent_type="Explore", prompt="Find all database migration code")
   ```

2. **Multi-language analysis**
   ```
   Task(subagent_type="coder:rust", prompt="Analyze Cargo.toml dependencies")
   Task(subagent_type="coder:typescript", prompt="Analyze package.json dependencies")
   ```

3. **Build + Test on different targets**
   ```
   Task(subagent_type="coder:rust", prompt="Build and test on junkpile")
   Task(subagent_type="coder:dx", prompt="Build WASM locally")
   ```

4. **Documentation generation**
   ```
   Task(subagent_type="coder:ruby", prompt="Document the models")
   Task(subagent_type="coder:ruby", prompt="Document the controllers")
   ```

### When NOT to Parallelize

**Sequential dependencies - must wait:**

1. **Build before test**
   - Don't: parallel build + test
   - Do: build, then test

2. **Generate before use**
   - Don't: parallel migration + seed
   - Do: migrate, then seed

3. **Research before implement**
   - Don't: parallel explore + code
   - Do: explore, understand, then implement

4. **File operations on same files**
   - Don't: parallel edits to same file
   - Do: sequential edits or batch in one agent

### Agent Selection for Parallel Work

| Scenario | Agents to Parallelize |
|----------|----------------------|
| Full-stack feature | `coder:typescript` (frontend) + `coder:ruby` (backend) |
| Cross-platform build | `coder:rust` (junkpile) + `coder:dx` (local) |
| Multi-repo changes | Multiple `coder` agents, one per repo |
| Deep codebase research | Multiple `Explore` agents with different queries |
| Infrastructure + Code | `devops` + `coder:*` |

### Cost-Benefit Analysis

```
Parallel agents cost:
- More context window usage
- More API calls
- Potential conflicts if touching same files

Parallel agents benefit:
- Reduced wall-clock time
- Better for independent tasks
- Can leverage different expertise

Use parallel when:
  benefit > cost
  AND tasks are truly independent
  AND combined time savings > overhead
```

## Combined Strategy: Background + Parallel

### Maximum Efficiency Pattern

```
1. Launch background builds on both targets:
   - Task(background, "cargo build --release on junkpile")
   - Task(background, "dx build --release locally")

2. While builds run, parallelize research:
   - Task(parallel, "Explore authentication code")
   - Task(parallel, "Explore authorization code")

3. Review research results

4. Check build outputs

5. If builds succeeded, parallelize tests:
   - Task(parallel, "Run rust tests on junkpile")
   - Task(parallel, "Run wasm tests locally")
```

### Remote Build Workflow (junkpile)

```bash
# 1. Sync code (fast, foreground)
rsync -avz --exclude target/ ./ junkpile:~/project/

# 2. Build remotely (slow, background)
Task(run_in_background=true, prompt="ssh junkpile 'cd ~/project && cargo build --release'")

# 3. Continue local work while building

# 4. Fetch binary when done (fast, foreground)
scp junkpile:~/project/target/release/binary ./
```

## Language-Specific Recommendations

### Rust

| Task | Strategy |
|------|----------|
| `cargo build` (debug) | Foreground if <30s, background otherwise |
| `cargo build --release` | Always background |
| `cargo test` | Background for full suite, foreground for single test |
| `cargo clippy` | Background on large codebases |
| Remote AMD64 build | Background with rsync + ssh |

### TypeScript

| Task | Strategy |
|------|----------|
| `pnpm install` | Background on fresh, foreground on incremental |
| `tsc --noEmit` | Foreground (fast with incremental) |
| `vitest run` | Foreground for targeted, background for full |
| `next build` | Background |

### Ruby

| Task | Strategy |
|------|----------|
| `bundle install` | Background (native gems are slow) |
| `rspec spec/file_spec.rb` | Foreground |
| `rspec` (full suite) | Background |
| `rails assets:precompile` | Background |

### Python

| Task | Strategy |
|------|----------|
| `uv sync` | Foreground (fast) |
| `pip install` | Background (slow) |
| `pytest tests/test_file.py` | Foreground |
| `pytest` (full suite) | Background |
| `mypy .` | Background on large codebases |

### Dioxus

| Task | Strategy |
|------|----------|
| `dx serve` | Foreground (interactive) |
| `dx build --release` | Background |
| `dx check` | Foreground (fast) |

## Decision Flowchart

```
Is the task < 30 seconds?
├─ Yes → Run foreground
└─ No → Do I need the result immediately?
         ├─ Yes → Run foreground, plan next steps while waiting
         └─ No → Run background
                  └─ Are there other independent tasks?
                      ├─ Yes → Parallelize those too
                      └─ No → Continue with other work
```

## Mandatory: Always Run Tests with Coverage

**Rule:** NEVER run tests without coverage. Running tests twice (once for pass/fail, once for coverage) wastes 2x the time.

| Language | Command | Tool |
|----------|---------|------|
| Ruby | `bundle exec rspec --format documentation` | SimpleCov (auto-loads) |
| Rust | `cargo llvm-cov nextest` | cargo-llvm-cov + nextest |
| Python | `pytest --cov=src --cov-report=term-missing` | pytest-cov |
| TypeScript | `vitest run --coverage` | vitest + @vitest/coverage-v8 |

**Why this matters:**
- Test suite takes the same time with or without coverage
- Coverage report is always useful information
- Running tests twice = 2x build time, 2x wait time
- 91% coverage target requires knowing current coverage

**The only exception:** Debugging a single failing test where you need rapid iteration:
```bash
# OK for rapid debug iteration only
pytest tests/test_specific.py::test_one_function -x
```

But once fixed, run full coverage to verify.

## Anti-Patterns

1. **Parallelizing dependent tasks** - Wastes resources, causes failures
2. **Backgrounding everything** - Loses track, harder to debug
3. **Too many parallel agents** - Context explosion, diminishing returns
4. **Ignoring build output** - Miss errors, waste time on broken builds
5. **Sequential when parallel is safe** - Unnecessary waiting

## Metrics to Watch

- **Wall-clock time**: Total time from start to finish
- **Agent count**: Keep parallel agents to 2-4 max
- **Build cache hits**: sccache stats show efficiency
- **Context usage**: Don't explode context with too many agents
