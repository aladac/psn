---
description: 'Use when writing Ruby code, implementing Ruby features, or needing Ruby best practices and idioms.'
---

# Ruby Coding Practices

Modern Ruby idioms focused on readability and maintainability.

## Module Organization

### Flat Namespace Declaration

```ruby
# Prefer: Flat declaration
module Foo::Bar::Baz
  def self.call
  end
end

# Avoid: Nested modules (unless you need to define parent modules)
module Foo
  module Bar
    module Baz
    end
  end
end
```

### Module Functions

```ruby
# Prefer: module_function for utility modules
module StringUtils
  module_function

  def truncate(str, length)
    str.length > length ? "#{str[0, length - 3]}..." : str
  end

  def slugify(str)
    str.downcase.strip.gsub(/\s+/, '-').gsub(/[^\w-]/, '')
  end
end
```

### Class-Level Singleton Methods

```ruby
module Api::Client
  class << self
    def get(url)
      # ...
    end

    private

    def connection
      @connection ||= Faraday.new
    end
  end
end
```

## Service Objects

Encapsulate business logic in callable objects:

```ruby
class CreateOrder
  def self.call(...)
    new(...).call
  end

  def initialize(user:, items:, coupon: nil)
    @user = user
    @items = items
    @coupon = coupon
  end

  def call
    return failure(:no_items) if @items.empty?
    return failure(:invalid_coupon) unless valid_coupon?

    order = build_order
    order.save ? success(order) : failure(order.errors)
  end

  private

  # ... helper methods
end
```

## Data Structures

### Data Classes (Ruby 3.2+)

```ruby
Order = Data.define(:id, :items, :status) do
  def total
    items.sum(&:price)
  end
end
```

### Struct (When Mutability Needed)

```ruby
Point = Struct.new(:x, :y, keyword_init: true) do
  def distance_from_origin
    Math.sqrt(x**2 + y**2)
  end
end
```

## Pattern Matching (Ruby 3.0+)

```ruby
case response
in { status: 200, body: }
  process(body)
in { status: 404 }
  handle_not_found
in { status: 500, error: message }
  log_error(message)
end
```

## Keyword Arguments

```ruby
# Always use keywords for clarity
fetch_data(url, use_cache: false, timeout: 30)

# Ruby 3.0+: Forward all arguments
def wrapper(...)
  wrapped_method(...)
end
```

## Error Handling

```ruby
module MyApp
  class Error < StandardError; end
  class ValidationError < Error; end
  class NotFoundError < Error; end
end

def fetch_user(id)
  api.get("/users/#{id}")
rescue Faraday::ResourceNotFound
  nil
rescue Faraday::TimeoutError => e
  raise MyApp::ApiError.new("Service unavailable", status: 503)
end
```

## Memoization

```ruby
# Simple
def current_user
  @current_user ||= User.find(session[:user_id])
end

# With Nil/False Values
def feature_enabled?
  return @feature_enabled if defined?(@feature_enabled)
  @feature_enabled = expensive_check
end
```

## dry-rb Stack

Prefer dry-rb gems where applicable:

| Need | Use |
|------|-----|
| Validation | `dry-validation` / `dry-schema` |
| Types & structs | `dry-types` / `dry-struct` |
| Dependency injection | `dry-auto_inject` + `dry-container` |
| Transactions | `dry-transaction` / `dry-monads` |

## Forbidden

Never commit:
- `binding.pry` or `byebug`
- `puts` / `p` for debugging
- Monkey-patching core classes
- `eval` with user input
- Wildcard rescues (`rescue => e`)
- Magic numbers (use named constants)
