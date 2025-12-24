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

To run checks locally, install dependencies:

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
