---
description: 'Use when building Rails applications, creating Rails APIs with RSwag, or implementing Rails patterns and conventions.'
---

# Ruby on Rails Development

Rails API with RSwag for OpenAPI documentation. Specs are tests AND docs.

## Quick Start

```bash
rails new myapi --api -T --database=postgresql
cd myapi
```

## Essential Gems

```ruby
# Gemfile
gem "rswag-api"
gem "rswag-ui"
gem "oj"                    # Fast JSON
gem "kaminari"              # Pagination

group :development, :test do
  gem "rspec-rails"
  gem "rswag-specs"
  gem "factory_bot_rails"
  gem "faker"
end
```

## Project Structure

```
myapi/
├── app/
│   ├── controllers/
│   │   └── api/
│   │       └── v1/
│   │           ├── base_controller.rb
│   │           └── users_controller.rb
│   ├── models/
│   └── services/          # Business logic
├── spec/
│   ├── factories/
│   ├── requests/
│   │   └── api/v1/
│   ├── support/
│   │   ├── api_helpers.rb
│   │   └── factory_bot.rb
│   ├── rails_helper.rb
│   └── swagger_helper.rb
└── swagger/
    └── v1/swagger.yaml    # Generated
```

## Base Controller

```ruby
# app/controllers/api/v1/base_controller.rb
module Api::V1
  class BaseController < ApplicationController
    rescue_from ActiveRecord::RecordNotFound do |e|
      render json: { error: "Not found" }, status: :not_found
    end

    rescue_from ActionController::ParameterMissing do |e|
      render json: { error: e.message }, status: :bad_request
    end

    private

    def authenticate!
      token = request.headers["Authorization"]&.split(" ")&.last
      @current_user = User.find_by_token(token)
      render json: { error: "Unauthorized" }, status: :unauthorized unless @current_user
    end
  end
end
```

## Resource Controller

```ruby
# app/controllers/api/v1/users_controller.rb
module Api::V1
  class UsersController < BaseController
    before_action :set_user, only: [:show, :update, :destroy]

    def index
      @users = User.all
      render json: @users
    end

    def show
      render json: @user
    end

    def create
      @user = User.new(user_params)
      if @user.save
        render json: @user, status: :created
      else
        render json: { errors: @user.errors }, status: :unprocessable_entity
      end
    end

    private

    def set_user
      @user = User.find(params[:id])
    end

    def user_params
      params.require(:user).permit(:name, :email)
    end
  end
end
```

## RSwag Spec (API Documentation)

```ruby
# spec/requests/api/v1/users_spec.rb
require "swagger_helper"

RSpec.describe "Users API", type: :request do
  path "/api/v1/users" do
    get "List users" do
      tags "Users"
      produces "application/json"

      response "200", "success" do
        schema type: :array, items: { "$ref" => "#/components/schemas/User" }

        before { create_list(:user, 3) }
        run_test!
      end
    end

    post "Create user" do
      tags "Users"
      consumes "application/json"
      produces "application/json"
      parameter name: :body, in: :body, schema: { "$ref" => "#/components/schemas/UserInput" }

      response "201", "created" do
        schema "$ref" => "#/components/schemas/User"
        let(:body) { { user: { name: "Alice", email: "alice@example.com" } } }
        run_test!
      end

      response "422", "validation failed" do
        let(:body) { { user: { name: "" } } }
        run_test!
      end
    end
  end

  path "/api/v1/users/{id}" do
    parameter name: :id, in: :path, type: :integer

    get "Get user" do
      tags "Users"
      produces "application/json"

      response "200", "found" do
        schema "$ref" => "#/components/schemas/User"
        let(:id) { create(:user).id }
        run_test!
      end

      response "404", "not found" do
        let(:id) { 0 }
        run_test!
      end
    end
  end
end
```

## Swagger Helper

```ruby
# spec/swagger_helper.rb
require "rails_helper"

RSpec.configure do |config|
  config.openapi_root = Rails.root.join("swagger").to_s

  config.openapi_specs = {
    "v1/swagger.yaml" => {
      openapi: "3.0.1",
      info: { title: "API V1", version: "v1" },
      paths: {},
      components: {
        schemas: {
          User: {
            type: :object,
            properties: {
              id: { type: :integer },
              name: { type: :string },
              email: { type: :string, format: :email }
            },
            required: %w[id name email]
          },
          Error: {
            type: :object,
            properties: { error: { type: :string } }
          }
        },
        securitySchemes: {
          bearer: { type: :http, scheme: :bearer }
        }
      }
    }
  }

  config.openapi_format = :yaml
end
```

## Service Objects

```ruby
# app/services/application_service.rb
class ApplicationService
  def self.call(...)
    new(...).call
  end

  private

  def success(data = {})
    Result.new(success: true, **data)
  end

  def failure(errors)
    Result.new(success: false, errors: Array(errors))
  end

  Result = Data.define(:success, :errors, :data) do
    alias_method :success?, :success
    def initialize(success:, errors: [], **data)
      super(success:, errors:, data:)
    end
  end
end

# app/services/orders/create.rb
module Orders
  class Create < ApplicationService
    def initialize(user:, items:)
      @user = user
      @items = items
    end

    def call
      return failure(:no_items) if @items.empty?

      order = Order.new(user: @user, items: @items)
      order.save ? success(order:) : failure(order.errors)
    end
  end
end
```

## Workflow

```bash
# Generate model/controller
rails g model User name:string email:string
rails g controller api/v1/users
rails db:migrate

# Write spec (defines API contract)
# Implement controller
# Generate docs
rails rswag:specs:swaggerize

# View at /api-docs
rails s
open http://localhost:3000/api-docs
```

## Summary

| Concern | Solution |
|---------|----------|
| Framework | Rails API mode |
| Documentation | RSwag (specs = docs) |
| Authentication | Bearer token |
| Pagination | Kaminari |
| Business logic | Service objects |
| Testing | RSpec request specs |
