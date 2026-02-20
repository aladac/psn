---
description: 'Use when creating Ruby gems, building reusable Ruby libraries, or publishing to RubyGems.org.'
---

# Ruby Gem Development

Best practices for creating and publishing Ruby gems.

## Create New Gem

```bash
bundle gem mylib
cd mylib
```

## Project Structure

```
mylib/
├── lib/
│   ├── mylib.rb           # Main entry point
│   ├── mylib/
│   │   ├── version.rb     # VERSION constant
│   │   ├── client.rb      # Core classes
│   │   └── errors.rb      # Custom exceptions
├── spec/
│   ├── spec_helper.rb
│   └── mylib_spec.rb
├── exe/                    # CLI executables (optional)
│   └── mylib
├── .rspec
├── Gemfile
├── mylib.gemspec
├── README.md
├── LICENSE.txt
└── CHANGELOG.md
```

## Gemspec

```ruby
# mylib.gemspec
Gem::Specification.new do |spec|
  spec.name          = "mylib"
  spec.version       = MyLib::VERSION
  spec.authors       = ["Your Name"]
  spec.email         = ["you@example.com"]

  spec.summary       = "A short description"
  spec.description   = "A longer description of your gem"
  spec.homepage      = "https://github.com/you/mylib"
  spec.license       = "MIT"
  spec.required_ruby_version = ">= 3.2"

  spec.metadata = {
    "homepage_uri"    => spec.homepage,
    "source_code_uri" => spec.homepage,
    "changelog_uri"   => "#{spec.homepage}/blob/main/CHANGELOG.md",
    "rubygems_mfa_required" => "true"
  }

  # Include only necessary files
  spec.files = Dir.glob(%w[
    lib/**/*
    exe/*
    LICENSE.txt
    README.md
    CHANGELOG.md
  ])

  spec.bindir        = "exe"
  spec.executables   = spec.files.grep(%r{\Aexe/}) { |f| File.basename(f) }
  spec.require_paths = ["lib"]

  # Runtime dependencies
  spec.add_dependency "faraday", "~> 2.0"
  spec.add_dependency "dry-struct", "~> 1.6"

  # Development dependencies go in Gemfile, not here
end
```

## Main Entry Point

```ruby
# lib/mylib.rb
require_relative "mylib/version"
require_relative "mylib/errors"
require_relative "mylib/client"
require_relative "mylib/config"

module MyLib
  class << self
    attr_writer :configuration

    def configuration
      @configuration ||= Config.new
    end

    def configure
      yield(configuration)
    end

    def reset_configuration!
      @configuration = Config.new
    end
  end
end
```

## Version

```ruby
# lib/mylib/version.rb
module MyLib
  VERSION = "0.1.0"
end
```

## Configuration Pattern

```ruby
# lib/mylib/config.rb
module MyLib
  class Config
    attr_accessor :api_key, :timeout, :debug

    def initialize
      @api_key = nil
      @timeout = 30
      @debug = false
    end
  end
end

# Usage
MyLib.configure do |config|
  config.api_key = "secret"
  config.timeout = 60
end
```

## Custom Exceptions

```ruby
# lib/mylib/errors.rb
module MyLib
  class Error < StandardError; end

  class ConfigurationError < Error; end

  class ApiError < Error
    attr_reader :status, :response

    def initialize(message, status: nil, response: nil)
      super(message)
      @status = status
      @response = response
    end
  end

  class NotFoundError < ApiError; end
  class AuthenticationError < ApiError; end
end
```

## Client Class

```ruby
# lib/mylib/client.rb
module MyLib
  class Client
    def initialize(api_key: nil)
      @api_key = api_key || MyLib.configuration.api_key
      raise ConfigurationError, "API key required" unless @api_key
    end

    def get_resource(id)
      response = connection.get("/resources/#{id}")
      handle_response(response)
    end

    private

    def connection
      @connection ||= Faraday.new(url: BASE_URL) do |f|
        f.request :json
        f.response :json
        f.adapter Faraday.default_adapter
        f.headers["Authorization"] = "Bearer #{@api_key}"
      end
    end

    def handle_response(response)
      case response.status
      when 200..299 then response.body
      when 401 then raise AuthenticationError.new("Unauthorized", status: 401)
      when 404 then raise NotFoundError.new("Not found", status: 404)
      else raise ApiError.new("API error", status: response.status)
      end
    end
  end
end
```

## Testing

```ruby
# spec/spec_helper.rb
require "mylib"

RSpec.configure do |config|
  config.before(:each) do
    MyLib.reset_configuration!
  end
end

# spec/mylib/client_spec.rb
describe MyLib::Client do
  let(:api_key) { "test-key" }
  let(:client) { described_class.new(api_key: api_key) }

  describe "#get_resource" do
    it "returns resource data" do
      stub_request(:get, "https://api.example.com/resources/123")
        .to_return(status: 200, body: '{"id": 123}')

      result = client.get_resource(123)
      expect(result["id"]).to eq(123)
    end

    it "raises NotFoundError for 404" do
      stub_request(:get, "https://api.example.com/resources/999")
        .to_return(status: 404)

      expect { client.get_resource(999) }
        .to raise_error(MyLib::NotFoundError)
    end
  end
end
```

## Gemfile

```ruby
# Gemfile
source "https://rubygems.org"

gemspec

group :development, :test do
  gem "rspec", "~> 3.13"
  gem "standard", "~> 1.35"
  gem "webmock", "~> 3.19"
  gem "vcr", "~> 6.2"
  gem "rake", "~> 13.0"
end
```

## Rake Tasks

```ruby
# Rakefile
require "bundler/gem_tasks"
require "rspec/core/rake_task"
require "standard/rake"

RSpec::Core::RakeTask.new(:spec)

task default: %i[spec standard]
```

## Release Process

```bash
# 1. Update version in lib/mylib/version.rb
# 2. Update CHANGELOG.md
# 3. Commit changes
git add -A
git commit -m "Release v0.2.0"

# 4. Create tag and push
git tag v0.2.0
git push origin main --tags

# 5. Build and publish
gem build mylib.gemspec
gem push mylib-0.2.0.gem

# Or use rake
rake release
```

## CI Configuration

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        ruby: ['3.2', '3.3']

    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: ${{ matrix.ruby }}
          bundler-cache: true

      - run: bundle exec rake
```

## Summary

| File | Purpose |
|------|---------|
| `mylib.gemspec` | Gem metadata, dependencies |
| `lib/mylib.rb` | Main entry, requires |
| `lib/mylib/version.rb` | Version constant |
| `lib/mylib/errors.rb` | Custom exceptions |
| `exe/mylib` | CLI executable (optional) |
| `CHANGELOG.md` | Release notes |
