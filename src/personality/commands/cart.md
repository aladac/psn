# Show or Switch Cart

Show the current personality cart or switch to a different one.

**Arguments:** $ARGUMENTS

If no argument provided:
- Read the `personality://cart` resource to show current cart details

If a cart name is provided:
- Update `~/.mcp.json` to set the new cart
- Inform user they need to restart the session for changes to take effect

Use `personality://carts` resource to list available carts if the requested cart is not found.
