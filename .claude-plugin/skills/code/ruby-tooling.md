---
description: 'Use for Ruby linting, formatting, type checking, test coverage, and project validation. Covers standardrb, rubocop, sorbet, and simplecov.'
---

# Ruby Tooling

Comprehensive guide to Ruby linting, formatting, type checking, and coverage.

## Linting: Standard Ruby (Recommended)

Modern "no config" linting based on RuboCop:

```ruby
# Gemfile
gem 'standard', group: [:development, :test]
```

### Commands

```bash
# Check
bundle exec standardrb

# Autofix
bundle exec standardrb --fix

# Generate TODO for gradual adoption
bundle exec standardrb --generate-todo
```

## Linting: RuboCop (Classic)

```ruby
# Gemfile
group :development, :test do
  gem 'rubocop', '~> 1.60', require: false
  gem 'rubocop-rails', require: false
  gem 'rubocop-rspec', require: false
  gem 'rubocop-performance', require: false
end
```

### Configuration

```yaml
# .rubocop.yml
require:
  - rubocop-rails
  - rubocop-rspec
  - rubocop-performance

AllCops:
  NewCops: enable
  TargetRubyVersion: 3.3
  Exclude:
    - 'db/schema.rb'
    - 'bin/*'
    - 'vendor/**/*'

Metrics/MethodLength:
  Max: 20

Metrics/ClassLength:
  Max: 200

Metrics/BlockLength:
  Exclude:
    - 'spec/**/*'
    - '*.gemspec'

Style/Documentation:
  Enabled: false
```

### Commands

```bash
# Check
bundle exec rubocop

# Autofix safe cops
bundle exec rubocop -a

# Autofix all (including unsafe)
bundle exec rubocop -A

# Generate TODO
bundle exec rubocop --auto-gen-config
```

## Type Checking: Sorbet

```ruby
# Gemfile
gem 'sorbet', group: :development
gem 'sorbet-runtime'
gem 'tapioca', group: :development
```

### Setup

```bash
bundle exec srb init
bundle exec tapioca init
bundle exec tapioca gems
```

### Commands

```bash
# Type check
bundle exec srb tc
```

### Signatures

```ruby
# typed: strict

class User
  extend T::Sig

  sig { params(name: String, email: String).void }
  def initialize(name:, email:)
    @name = name
    @email = email
  end

  sig { returns(String) }
  attr_reader :name, :email
end
```

## Type Checking: RBS + Steep

```ruby
# Gemfile
gem 'rbs', group: :development
gem 'steep', group: :development
```

### Commands

```bash
bundle exec steep check
bundle exec rbs prototype rb lib/user.rb > sig/user.rbs
```

## Test Coverage: SimpleCov

```ruby
# Gemfile
gem 'simplecov', require: false, group: :test
```

### Configuration

```ruby
# spec/spec_helper.rb (at the very top)
require 'simplecov'
SimpleCov.start do
  add_filter '/spec/'
  add_filter '/config/'
  add_group 'Models', 'app/models'
  add_group 'Services', 'app/services'
  minimum_coverage 90
end
```

### Commands

```bash
# Run tests with coverage
bundle exec rspec

# Coverage report in coverage/index.html
open coverage/index.html
```

## All-in-One: Rake Tasks

```ruby
# Rakefile
require 'rspec/core/rake_task'
require 'standard/rake'

RSpec::Core::RakeTask.new(:spec)

desc 'Run all checks'
task check: [:standard, :spec]

desc 'Run checks with autofix'
task fix: ['standard:fix']

task default: :check
```

## Project Validation

Run all checks:

```bash
# With Standard Ruby
bundle exec standardrb && bundle exec rspec

# With RuboCop + Sorbet
bundle exec rubocop && bundle exec srb tc && bundle exec rspec

# With coverage
COVERAGE=true bundle exec rspec
```

## CI Configuration

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3'
          bundler-cache: true

      - name: Lint
        run: bundle exec standardrb

      - name: Type check
        run: bundle exec srb tc

      - name: Test
        run: bundle exec rspec
```

## Quick Reference

| Operation | Standard Ruby | RuboCop |
|-----------|--------------|---------|
| Lint check | `standardrb` | `rubocop` |
| Lint fix | `standardrb --fix` | `rubocop -A` |
| Type check | `srb tc` | `steep check` |
| Format | (included in lint) | (included in lint) |
| Coverage | `rspec` + simplecov | `rspec` + simplecov |
| All checks | `rake check` | `rake check` |

## Recommended Stack

- **Lint/Format**: Standard Ruby (no config debates)
- **Types**: Sorbet for new projects
- **Testing**: RSpec with SimpleCov
