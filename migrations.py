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
        f"""
        CREATE TABLE nostrmarket.products (
            user_id TEXT NOT NULL,
            id TEXT PRIMARY KEY,
            stall_id TEXT NOT NULL,
            name TEXT NOT NULL,
            category_list TEXT DEFAULT '[]',
            description TEXT,
            images TEXT DEFAULT '[]',
            price REAL NOT NULL,
            quantity INTEGER NOT NULL
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
    await db.execute(
        f"""
        CREATE TABLE nostrmarket.orders (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            username TEXT,
            pubkey TEXT,
            shipping_zone TEXT NOT NULL,
            address TEXT,
            email TEXT,
            total REAL NOT NULL,
            invoice_id TEXT NOT NULL,
            paid BOOLEAN NOT NULL,
            shipped BOOLEAN NOT NULL,
            time TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
        """
    )

    """
    Initial order details table.
    """
    await db.execute(
        f"""
        CREATE TABLE nostrmarket.order_details (
            id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            quantity INTEGER NOT NULL
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
    Initial market stalls table.
    """
    await db.execute(
        f"""
        CREATE TABLE nostrmarket.market_stalls (
            id TEXT PRIMARY KEY,
            market_id TEXT NOT NULL,
            stall_id TEXT NOT NULL
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
