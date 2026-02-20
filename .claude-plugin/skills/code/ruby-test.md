---
description: 'Use when writing Ruby tests, setting up RSpec, creating test doubles, or implementing test patterns in Ruby.'
---

# Ruby Testing

Comprehensive guide to testing Ruby with RSpec.

## Installation

```ruby
# Gemfile
group :test do
  gem 'rspec', '~> 3.13'
  gem 'rspec-rails', '~> 6.0' # For Rails projects
  gem 'factory_bot_rails'
  gem 'faker'
end
```

## Configuration

```ruby
# .rspec
--require spec_helper
--format documentation
--color

# spec/spec_helper.rb
RSpec.configure do |config|
  config.expose_dsl_globally = true  # Use describe, not RSpec.describe
  config.filter_run_when_matching :focus
  config.example_status_persistence_file_path = 'spec/examples.txt'

  config.expect_with :rspec do |expectations|
    expectations.include_chain_clauses_in_custom_matcher_descriptions = true
  end

  config.mock_with :rspec do |mocks|
    mocks.verify_partial_doubles = true
  end
end
```

## Structure (Readable First)

```ruby
describe Order do
  describe '#apply_discount' do
    context 'when order total exceeds threshold' do
      let(:order) { Order.new(total: 150) }

      it 'applies percentage discount' do
        order.apply_discount(10)
        expect(order.total).to eq(135)
      end
    end

    context 'when order total is below threshold' do
      let(:order) { Order.new(total: 50) }

      it 'does not modify total' do
        order.apply_discount(10)
        expect(order.total).to eq(50)
      end
    end

    context 'with invalid discount percentage' do
      it 'raises ArgumentError for negative values' do
        expect { order.apply_discount(-5) }
          .to raise_error(ArgumentError, /positive/)
      end
    end
  end
end
```

## Shared Examples

```ruby
# spec/support/shared_examples/validatable.rb
shared_examples 'validatable' do
  describe '#valid?' do
    context 'with valid attributes' do
      it 'returns true' do
        expect(subject).to be_valid
      end
    end
  end
end

# Usage
describe User do
  subject { User.new(name: 'Alice', email: 'alice@example.com') }
  it_behaves_like 'validatable'
end
```

## Factories (FactoryBot)

```ruby
# spec/factories/users.rb
FactoryBot.define do
  factory :user do
    name { 'Alice' }
    sequence(:email) { |n| "user#{n}@example.com" }

    trait :admin do
      role { 'admin' }
    end

    trait :with_orders do
      transient do
        orders_count { 3 }
      end

      after(:create) do |user, evaluator|
        create_list(:order, evaluator.orders_count, user: user)
      end
    end
  end
end

# Usage
create(:user)
create(:user, :admin)
create(:user, :with_orders, orders_count: 5)
```

## Test Doubles

```ruby
describe OrderService do
  describe '#process' do
    let(:payment_gateway) { instance_double(PaymentGateway) }
    let(:service) { OrderService.new(gateway: payment_gateway) }

    before do
      allow(payment_gateway).to receive(:charge).and_return(true)
    end

    it 'charges the payment gateway' do
      service.process(order)
      expect(payment_gateway).to have_received(:charge).with(order.total)
    end
  end
end
```

## Commands

```bash
# Run all specs
bundle exec rspec

# Run specific file
bundle exec rspec spec/models/user_spec.rb

# Run specific line
bundle exec rspec spec/models/user_spec.rb:42

# Run by tag
bundle exec rspec --tag focus
bundle exec rspec --tag ~slow  # Exclude slow

# Fail fast
bundle exec rspec --fail-fast

# Format options
bundle exec rspec --format documentation
bundle exec rspec --format json --out results.json
```

## Request Specs (Rails API)

```ruby
# spec/requests/api/v1/users_spec.rb
describe "Users API", type: :request do
  describe "GET /api/v1/users" do
    it "returns users" do
      create_list(:user, 3)

      get "/api/v1/users", headers: auth_headers

      expect(response).to have_http_status(:ok)
      expect(json_body.length).to eq(3)
    end
  end
end

# spec/support/api_helpers.rb
module ApiHelpers
  def json_body
    JSON.parse(response.body, symbolize_names: true)
  end

  def auth_headers(user = nil)
    user ||= create(:user)
    { "Authorization" => "Bearer #{user.auth_token}" }
  end
end

RSpec.configure do |config|
  config.include ApiHelpers, type: :request
end
```

## Test File Mirroring

```
# Source                          # Test
lib/something/something_else.rb → spec/something/something_else_spec.rb
app/models/user.rb              → spec/models/user_spec.rb
app/services/orders/create.rb   → spec/services/orders/create_spec.rb
```

## CI Configuration

```yaml
# .github/workflows/ci.yml
- name: Test
  run: bundle exec rspec
```

## Summary

| Component | Library |
|-----------|---------|
| Framework | `rspec` |
| Factories | `factory_bot` |
| Fake data | `faker` |
| Time travel | `timecop` or Rails `travel_to` |
| HTTP mocking | `webmock`, `vcr` |
