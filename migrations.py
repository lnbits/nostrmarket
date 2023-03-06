async def m001_initial(db):

    """
    Initial merchants table.
    """
    await db.execute(
        """
        CREATE TABLE nostrmarket.merchants (
            user_id TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            private_key TEXT NOT NULL,
            public_key TEXT NOT NULL,
            meta TEXT NOT NULL DEFAULT '{}'
        );
        """
    )

    """
    Initial stalls table.
    """
    # user_id, id, wallet, name, currency, zones, meta
    await db.execute(
        """
        CREATE TABLE nostrmarket.stalls (
            user_id TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            name TEXT NOT NULL,
            currency TEXT,
            zones TEXT NOT NULL DEFAULT '[]',
            meta TEXT NOT NULL DEFAULT '{}'
        );
        """
    )

    """
    Initial products table.
    """
    await db.execute(
        """
        CREATE TABLE nostrmarket.products (
            user_id TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            stall_id TEXT NOT NULL,
            name TEXT NOT NULL,
            image TEXT DEFAULT,
            price REAL NOT NULL,
            quantity INTEGER NOT NULL,
            category_list TEXT DEFAULT '[]',
            meta TEXT NOT NULL DEFAULT '{}'
        );
        """
    )

    """
    Initial zones table.
    """
    await db.execute(
        """
        CREATE TABLE nostrmarket.zones (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            currency TEXT NOT NULL,
            cost REAL NOT NULL,
            regions TEXT NOT NULL DEFAULT '[]'
        );
        """
    )

    """
    Initial orders table.
    """
    empty_object = "{}"
    await db.execute(
        f"""
        CREATE TABLE nostrmarket.orders (
            user_id TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            event_id TEXT,
            pubkey EXT NOT NULL,
            contact_data TEXT NOT NULL DEFAULT '{empty_object}',
            order_items TEXT NOT NULL,
            address TEXT,
            total REAL NOT NULL,
            invoice_id TEXT NOT NULL,
            paid BOOLEAN NOT NULL DEFAULT false,
            shipped BOOLEAN NOT NULL DEFAULT false,
            time TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
        """
    )

    """
    Initial market table.
    """
    await db.execute(
        """
        CREATE TABLE nostrmarket.markets (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT
        );
        """
    )

    """
    Initial chat messages table.
    """
    await db.execute(
        f"""
        CREATE TABLE nostrmarket.messages (
            id TEXT PRIMARY KEY,
            msg TEXT NOT NULL,
            pubkey TEXT NOT NULL,
            conversation_id TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}       
            );
        """
    )

    if db.type != "SQLITE":
        """
        Create indexes for message fetching
        """
        await db.execute(
            "CREATE INDEX idx_messages_timestamp ON nostrmarket.messages (timestamp DESC)"
        )
        await db.execute(
            "CREATE INDEX idx_messages_conversations ON nostrmarket.messages (conversation_id)"
        )
