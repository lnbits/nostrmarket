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

    await db.execute(
        """
        CREATE TABLE nostrmarket.stalls (
            merchant_id TEXT NOT NULL,
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
            merchant_id TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            stall_id TEXT NOT NULL,
            name TEXT NOT NULL,
            image TEXT,
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
            merchant_id TEXT NOT NULL,
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
            merchant_id TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            event_id TEXT,
            event_created_at INTEGER NOT NULL,
            public_key TEXT NOT NULL,
            merchant_public_key TEXT NOT NULL,
            contact_data TEXT NOT NULL DEFAULT '{empty_object}',
            extra_data TEXT NOT NULL DEFAULT '{empty_object}',
            order_items TEXT NOT NULL,
            address TEXT,
            total REAL NOT NULL,
            stall_id TEXT NOT NULL,
            invoice_id TEXT NOT NULL,
            paid BOOLEAN NOT NULL DEFAULT false,
            shipped BOOLEAN NOT NULL DEFAULT false,
            time TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            UNIQUE(event_id)
        );
        """
    )

    """
    Initial chat messages table.
    """
    await db.execute(
        f"""
        CREATE TABLE nostrmarket.direct_messages (
            merchant_id TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            event_id TEXT,
            event_created_at INTEGER NOT NULL,
            message TEXT NOT NULL,
            public_key TEXT NOT NULL,
            incoming BOOLEAN NOT NULL DEFAULT false,
            time TIMESTAMP NOT NULL DEFAULT {db.timestamp_now},
            UNIQUE(event_id)
        );
        """
    )

    if db.type != "SQLITE":
        """
        Create indexes for message fetching
        """
        await db.execute(
            "CREATE INDEX idx_messages_timestamp ON nostrmarket.direct_messages (time DESC)"
        )
        await db.execute(
            "CREATE INDEX idx_event_id ON nostrmarket.direct_messages (event_id)"
        )
