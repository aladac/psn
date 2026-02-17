---
description: 'Use when building Ruby command-line applications, creating CLI tools with Thor, or implementing terminal interfaces in Ruby.'
---

# Ruby CLI Development

Best practices for Ruby command-line applications using Thor.

## Framework: Thor

Thor is the standard for Ruby CLIs (used by Rails, Bundler, etc.):

```ruby
# lib/myapp/cli.rb
require "thor"

module MyApp
  class CLI < Thor
    package_name "myapp"

    desc "process FILE", "Process a file"
    option :verbose, type: :boolean, aliases: "-v"
    option :output, type: :string, aliases: "-o", default: "output.txt"
    def process(file)
      # Implementation
    end

    desc "version", "Show version"
    map %w[-v --version] => :version
    def version
      puts "myapp #{MyApp::VERSION}"
    end

    def self.exit_on_failure?
      true
    end
  end
end
```

### Executable

```ruby
# exe/myapp
#!/usr/bin/env ruby
require "myapp"
MyApp::CLI.start(ARGV)
```

## Required Flags

| Flag | Purpose |
|------|---------|
| `--version`, `-v` | Show gem version |
| `--help`, `-h` | Show usage (Thor provides automatically) |

## Subcommands

```ruby
module MyApp
  class ConfigCLI < Thor
    desc "show", "Show current config"
    def show
      # ...
    end

    desc "set KEY VALUE", "Set config value"
    def set(key, value)
      # ...
    end
  end

  class CLI < Thor
    desc "config SUBCOMMAND", "Manage configuration"
    subcommand "config", ConfigCLI
  end
end
```

## Output Patterns

### Colorized Output

```ruby
require "pastel"

class CLI < Thor
  def initialize(*)
    super
    @pastel = Pastel.new
  end

  private

  def success(message)
    say @pastel.green("✓ #{message}")
  end

  def error(message)
    say @pastel.red("✗ #{message}"), :stderr
  end

  def warn(message)
    say @pastel.yellow("⚠ #{message}")
  end
end
```

### Tables

```ruby
require "terminal-table"

def list
  rows = items.map { |i| [i.id, i.name, i.status] }
  table = Terminal::Table.new(
    headings: ["ID", "Name", "Status"],
    rows: rows
  )
  puts table
end
```

### Progress Bars

```ruby
require "tty-progressbar"

def process_files(files)
  bar = TTY::ProgressBar.new("Processing [:bar] :percent", total: files.count)
  files.each do |file|
    process(file)
    bar.advance
  end
end
```

## Configuration

```ruby
require "tomlrb"

module MyApp
  class Config
    CONFIG_PATH = File.expand_path("~/.config/myapp/config.toml")

    def self.load
      return {} unless File.exist?(CONFIG_PATH)
      Tomlrb.load_file(CONFIG_PATH)
    end
  end
end
```

## Error Handling

```ruby
class CLI < Thor
  def process(file)
    result = MyApp::Processor.call(file)
    if result.success?
      success("Processed #{file}")
    else
      error(result.error)
      exit 1
    end
  rescue MyApp::Error => e
    error(e.message)
    exit 1
  rescue Interrupt
    warn("\nAborted")
    exit 130
  end
end
```

## Interactive Prompts

```ruby
require "tty-prompt"

def setup
  prompt = TTY::Prompt.new
  api_key = prompt.ask("API Key:") { |q| q.required true }
  env = prompt.select("Environment:", %w[development staging production])
  if prompt.yes?("Save configuration?")
    save_config(api_key: api_key, env: env)
  end
end
```

## Gemspec Setup

```ruby
Gem::Specification.new do |spec|
  spec.name = "myapp"
  spec.executables = ["myapp"]
  spec.bindir = "exe"

  spec.add_dependency "thor", "~> 1.3"
  spec.add_dependency "pastel", "~> 0.8"
  spec.add_dependency "tty-prompt", "~> 0.23"
  spec.add_dependency "tty-progressbar", "~> 0.18"
  spec.add_dependency "terminal-table", "~> 3.0"
  spec.add_dependency "tomlrb", "~> 2.0"
end
```

## Project Structure

```
myapp/
├── exe/
│   └── myapp              # Executable entry point
├── lib/
│   ├── myapp.rb           # Main require file
│   ├── myapp/
│   │   ├── cli.rb         # Thor CLI class
│   │   ├── config.rb      # Configuration handling
│   │   ├── version.rb     # VERSION constant
│   │   └── commands/      # Complex command implementations
├── spec/
│   ├── cli_spec.rb
│   └── commands/
└── myapp.gemspec
```

## Summary

| Component | Library |
|-----------|---------|
| CLI framework | `thor` |
| Colors | `pastel` |
| Prompts | `tty-prompt` |
| Progress | `tty-progressbar` |
| Tables | `terminal-table` |
| Config | `tomlrb` |
