---
description: 'Use when building Rust command-line applications, creating CLI tools with Clap, or implementing terminal interfaces in Rust.'
---

# Rust CLI Development

Best practices for Rust command-line applications using Clap.

## Framework: Clap (Derive)

```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "myapp")]
#[command(about = "Does useful things", version, author)]
struct Cli {
    /// Enable verbose output
    #[arg(short, long, global = true)]
    verbose: bool,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Process a file
    Process {
        /// Input file path
        file: PathBuf,
        /// Output file path
        #[arg(short, long)]
        output: Option<PathBuf>,
    },
    /// Show configuration
    Config {
        #[command(subcommand)]
        action: ConfigAction,
    },
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Process { file, output } => {
            process_file(&file, output.as_deref(), cli.verbose)?;
        }
        Commands::Config { action } => match action {
            ConfigAction::Show => show_config()?,
            ConfigAction::Set { key, value } => set_config(&key, &value)?,
        },
    }

    Ok(())
}
```

## Required Flags

| Flag | Purpose | How |
|------|---------|-----|
| `--version`, `-V` | Show version | `#[command(version)]` |
| `--help`, `-h` | Show usage | Automatic with Clap |

## Two-Level Run Pattern (Testable)

```rust
// Public entry - creates real dependencies
pub async fn run(args: Args) -> Result<()> {
    let config = Config::load()?;
    let client = Client::new(&config)?;
    run_with(&client, &args).await
}

// Testable - accepts trait objects
async fn run_with(client: &impl Api, args: &Args) -> Result<()> {
    let data = client.fetch(&args.query).await?;
    Ok(())
}

#[cfg(test)]
mod tests {
    struct MockClient;
    impl Api for MockClient {
        async fn fetch(&self, _: &str) -> Result<Data> {
            Ok(Data::default())
        }
    }
}
```

## Output Patterns

### Colorized Output

```rust
use owo_colors::OwoColorize;

fn success(message: &str) {
    println!("{} {}", "✓".green(), message);
}

fn error(message: &str) {
    eprintln!("{} {}", "✗".red(), message);
}

fn warn(message: &str) {
    eprintln!("{} {}", "⚠".yellow(), message);
}
```

### Tables

```rust
use comfy_table::{Table, presets::UTF8_FULL};

fn list_items(items: &[Item]) {
    let mut table = Table::new();
    table.load_preset(UTF8_FULL);
    table.set_header(vec!["ID", "Name", "Status"]);
    for item in items {
        table.add_row(vec![&item.id, &item.name, &item.status]);
    }
    println!("{table}");
}
```

### Progress Bars

```rust
use indicatif::{ProgressBar, ProgressStyle};

fn process_files(files: &[PathBuf]) -> Result<()> {
    let bar = ProgressBar::new(files.len() as u64);
    bar.set_style(
        ProgressStyle::default_bar()
            .template("{spinner:.green} [{bar:40}] {pos}/{len} {msg}")?
    );
    for file in files {
        bar.set_message(file.display().to_string());
        process_file(file)?;
        bar.inc(1);
    }
    bar.finish_with_message("Done");
    Ok(())
}
```

## Configuration

```rust
use serde::{Deserialize, Serialize};

#[derive(Debug, Deserialize, Serialize)]
pub struct Config {
    pub api_key: Option<String>,
    pub timeout: u64,
    #[serde(default)]
    pub debug: bool,
}

impl Config {
    pub fn path() -> PathBuf {
        dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("myapp")
            .join("config.toml")
    }

    pub fn load() -> Result<Self> {
        let path = Self::path();
        if !path.exists() { return Ok(Self::default()); }
        let content = std::fs::read_to_string(&path)?;
        Ok(toml::from_str(&content)?)
    }
}
```

## Error Handling

```rust
use anyhow::{Context, Result, bail};

fn process_file(path: &Path) -> Result<()> {
    let content = std::fs::read_to_string(path)
        .context(format!("failed to read {}", path.display()))?;

    if content.is_empty() {
        bail!("file is empty: {}", path.display());
    }
    Ok(())
}

fn main() {
    if let Err(e) = run() {
        error(&format!("{e:#}"));
        std::process::exit(1);
    }
}
```

## Interactive Prompts

```rust
use dialoguer::{Input, Select, Confirm, Password};

fn setup() -> Result<()> {
    let api_key: String = Password::new()
        .with_prompt("API Key")
        .interact()?;

    let env = Select::new()
        .with_prompt("Environment")
        .items(&["development", "staging", "production"])
        .default(0)
        .interact()?;

    if Confirm::new().with_prompt("Save configuration?").interact()? {
        let config = Config { api_key: Some(api_key), /* ... */ };
        config.save()?;
        success("Configuration saved");
    }
    Ok(())
}
```

## Cargo.toml Setup

```toml
[dependencies]
clap = { version = "4", features = ["derive"] }
anyhow = "1"
serde = { version = "1", features = ["derive"] }
toml = "0.8"
dirs = "5"
owo-colors = "4"
comfy-table = "7"
indicatif = "0.17"
dialoguer = "0.11"
tokio = { version = "1", features = ["rt-multi-thread", "macros", "signal"] }

[dev-dependencies]
assert_cmd = "2"
predicates = "3"
tempfile = "3"
```

## Project Structure

```
myapp/
├── src/
│   ├── main.rs             # Entry point, CLI parsing
│   ├── commands/           # Command implementations
│   │   ├── mod.rs
│   │   ├── process.rs
│   │   └── config.rs
│   ├── config.rs           # Configuration handling
│   └── output.rs           # success/error/warn helpers
├── tests/
│   └── cli.rs              # Integration tests
├── Cargo.toml
└── README.md
```

## Summary

| Component | Crate |
|-----------|-------|
| CLI framework | `clap` |
| Errors | `anyhow` |
| Colors | `owo-colors` |
| Tables | `comfy-table` |
| Progress | `indicatif` |
| Prompts | `dialoguer` |
| Config | `serde` + `toml` + `dirs` |
| Testing | `assert_cmd` + `predicates` |
