# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nostr Market is an LNbits extension implementing NIP-15 (decentralized marketplace protocol) on Nostr. It enables merchants to create webshops (stalls) and sell products with Lightning Network payments, featuring encrypted customer-merchant communication via NIP-04.

**Prerequisites:** Requires the LNbits [nostrclient](https://github.com/lnbits/nostrclient) extension to be installed and configured.

## Common Commands

All commands are in the Makefile:

```bash
make format      # Run prettier, black, and ruff formatters
make check       # Run mypy, pyright, black check, ruff check, prettier check
make test        # Run pytest with debug mode
make all         # Run format and check
```

Individual tools:

```bash
make black       # Format Python files
make ruff        # Check and fix Python linting
make mypy        # Static type checking
make pyright     # Python static type checker
make prettier    # Format JS/HTML/CSS files
```

## Local Development Setup

**Issues**: https://github.com/lnbits/nostrmarket/issues
**PRs**: https://github.com/lnbits/nostrmarket/pulls

### Extension Development with LNbits

This extension must be run inside LNbits. To set up:

1. Clone LNbits to a sibling directory:
   ```bash
   cd ..
   git clone https://github.com/lnbits/lnbits.git
   ```

2. Create a symbolic link from LNbits extensions to this directory:
   ```bash
   cd lnbits/lnbits/extensions
   ln -s ../../../nostrmarket nostrmarket
   ```

3. Configure your development environment:
   ```bash
   # Copy the example file
   cp .env.dev.example .env.dev
   # Edit .env.dev to point to your LNbits installation if needed
   ```

4. Use slash commands to manage the dev server:
   - `/run` - Start LNbits dev server in background
   - `/stop` - Stop the LNbits dev server

### Installing Dependencies

```bash
# Install Python autotools dependencies (needed for secp256k1)
sudo apt-get install -y automake autoconf libtool

# Install Python dependencies
uv sync

# Install Node dependencies (for prettier)
npm install

# Run all checks
make check
```

## Architecture

### Core Layers

1. **API Layer** (`views_api.py`) - REST endpoints for merchants, stalls, products, zones, orders, direct messages
2. **Business Logic** (`services.py`) - Order processing, Nostr event signing/publishing, message routing, invoice handling
3. **Data Layer** (`crud.py`) - Async SQLite operations via LNbits db module
4. **Models** (`models.py`) - Pydantic models for all entities

### Nostr Integration (`nostr/`)

- `nostr_client.py` - WebSocket client connecting to nostrclient extension for relay communication
- `event.py` - Nostr event model, serialization, ID computation (SHA256), Schnorr signatures

### Background Tasks (`__init__.py`, `tasks.py`)

Three permanent async tasks:

- `wait_for_paid_invoices()` - Lightning payment listener
- `wait_for_nostr_events()` - Incoming Nostr message processor
- `_subscribe_to_nostr_client()` - WebSocket connection manager

### Frontend (`static/`, `templates/`)

- Merchant dashboard: `templates/nostrmarket/index.html`
- Customer marketplace: `templates/nostrmarket/market.html` with Vue.js/Quasar in `static/market/`
- Use Quasar UI components when possible: https://quasar.dev/components

### Key Data Models

- **Merchant** - Shop owner with Nostr keypair, handles event signing and DM encryption
- **Stall** - Individual shop with products and shipping zones (kind 30017)
- **Product** - Items for sale with categories, images, quantity (kind 30018)
- **Zone** - Shipping configuration by region
- **Order** - Customer purchases with Lightning invoice tracking
- **DirectMessage** - Encrypted chat (NIP-04)
- **Customer** - Buyer profile with Nostr pubkey

### Key Patterns

- **Nostrable Interface** - Base class for models convertible to Nostr events (`to_nostr_event()`, `to_nostr_delete_event()`)
- **Parameterized Replaceable Events** - Stalls (kind 30017) and Products (kind 30018) per NIP-33
- **AES-256 Encryption** - Customer-merchant DMs use shared secret from ECDH
- **JSON Meta Fields** - Complex data (zones, items, config) stored as JSON in database

### Cryptography (`helpers.py`)

- Schnorr signatures for Nostr events
- NIP-04 encryption/decryption
- Key derivation and bech32 encoding (npub/nsec)

## Workflow

- Always check GitHub Actions after pushing to verify CI passes
- Run `make check` locally before pushing to catch issues early

---

## Claude Code Best Practices

### Before Making Changes

1. **Read before editing** - Always read the file before making changes
2. **Understand the pattern** - Check similar existing code for conventions
3. **Run checks** - Use `make check` before committing

### Frontend Development (Vue.js/Quasar)

#### Component Structure

Components are split across two files:
- **Template**: `templates/nostrmarket/components/<name>.html`
- **JavaScript**: `static/components/<name>.js`

```javascript
// Component JS pattern
window.app.component('component-name', {
  name: 'component-name',
  template: '#component-name',
  delimiters: ['${', '}'],  // Avoid Jinja2 conflicts
  props: ['prop-name'],     // kebab-case in template, camelCase in JS
  emits: ['event-name'],    // Declare all emitted events
  data: function () {
    return { /* reactive state */ }
  },
  computed: { /* computed properties */ },
  methods: { /* methods */ },
  watch: { /* watchers */ }
})
```

#### Template Registration

Templates must be registered in `index.html`:
```html
<template id="component-name">
  {% include("nostrmarket/components/component-name.html") %}
</template>
```

And JS loaded:
```html
<script src="{{ static_url_for('nostrmarket/static', path='components/component-name.js') }}"></script>
```

#### Quasar Components

- Use Quasar components: https://quasar.dev/components
- Common patterns:
  - `q-dialog` with `v-model` for dialogs
  - `q-input` with `:model-value` for readonly, `v-model` for editable
  - `q-btn` with `@click` for actions
  - `q-notify` via `this.$q.notify()` for notifications

#### LNbits API Calls

```javascript
// GET request
const {data} = await LNbits.api.request(
  'GET',
  '/nostrmarket/api/v1/endpoint',
  this.inkey  // or this.adminkey for write operations
)

// POST/PUT/PATCH/DELETE
await LNbits.api.request(
  'POST',
  '/nostrmarket/api/v1/endpoint',
  this.adminkey,
  payload
)

// Error handling
try {
  await LNbits.api.request(...)
} catch (error) {
  LNbits.utils.notifyApiError(error)
}
```

#### Confirmation Dialogs

```javascript
LNbits.utils.confirmDialog('Are you sure?')
  .onOk(async () => {
    // User confirmed
  })
```

### Backend Development (Python/FastAPI)

#### API Endpoints

```python
@nostrmarket_ext.post("/api/v1/resource")
async def api_create_resource(
    data: ResourceModel,
    wallet: WalletTypeInfo = Depends(require_admin_key),
) -> Resource:
    try:
        # Validation
        assert condition, "Error message"

        # Business logic
        resource = await create_resource(wallet.wallet.user, data)
        return resource

    except AssertionError as ex:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail=str(ex),
        ) from ex
    except Exception as ex:
        logger.warning(ex)
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Cannot create resource",
        ) from ex
```

#### CRUD Operations

```python
# crud.py pattern
async def create_resource(user_id: str, data: ResourceModel) -> Resource:
    resource_id = urlsafe_short_hash()
    await db.execute(
        """
        INSERT INTO nostrmarket.resources (id, user_id, ...)
        VALUES (:id, :user_id, ...)
        """,
        {"id": resource_id, "user_id": user_id, ...},
    )
    return await get_resource(user_id, resource_id)
```

#### Pydantic Models

```python
class ResourceModel(BaseModel):
    name: str
    optional_field: str | None = None

class Resource(ResourceModel):
    id: str
    time: int | None = 0
```

### Nostr Integration

#### Using MCP Nostr Tools

Claude Code has access to Nostr documentation via MCP:
- `mcp__nostrbook__read_nip` - Read NIP documentation
- `mcp__nostrbook__read_kind` - Read event kind docs
- `mcp__nostrbook__fetch_event` - Fetch events by nip19 identifier

#### Event Creation Pattern

```python
def to_nostr_event(self, pubkey: str) -> NostrEvent:
    content: dict[str, str] = {}
    if self.field:
        content["field"] = self.field

    event = NostrEvent(
        pubkey=pubkey,
        created_at=round(time.time()),
        kind=0,  # or appropriate kind
        tags=[],
        content=json.dumps(content, separators=(",", ":"), ensure_ascii=False),
    )
    event.id = event.event_id
    return event
```

### Git Workflow

1. **Branch naming**: `feature/<description>` or `fix/<description>`
2. **Commit messages**: Use conventional commits (`feat:`, `fix:`, `chore:`, etc.)
3. **Before pushing**: Always run `make check`
4. **PR comments**: Add context about changes and any WIP items

### Slash Commands

Available Claude Code commands in `.claude/commands/`:

- `/commit` - Run checks and commit changes with proper message
- `/format` - Format code with prettier, black, and ruff
- `/pr` - Create a pull request with summary and test plan
- `/push` - Push changes and monitor GitHub Actions
- `/run` - Start LNbits dev server in background
- `/stop` - Stop the LNbits dev server

### Common Gotchas

1. **Vue delimiters** - Use `${...}` not `{{...}}` (conflicts with Jinja2)
2. **Props naming** - kebab-case in HTML (`public-key`), camelCase in JS (`publicKey`)
3. **Icon names** - Use Material Icons: https://fonts.google.com/icons (e.g., `vpn_key` not `key`)
4. **Async/await** - Remember to `await` API calls
5. **Event emits** - Declare all emits in component's `emits` array
6. **Formatting** - Run `make prettier` for JS/HTML, `make black` for Python
