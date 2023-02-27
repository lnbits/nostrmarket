async def m001_initial(db):
    """
    Initial Market settings table.
    """
    await db.execute(
        """
        CREATE TABLE market.settings (
            "user" TEXT PRIMARY KEY,
            currency TEXT DEFAULT 'sat',
            fiat_base_multiplier INTEGER DEFAULT 1
        );
    """
    )

    """
    Initial stalls table.
    """
    await db.execute(
        """
        CREATE TABLE market.stalls (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            name TEXT NOT NULL,
            currency TEXT,
            publickey TEXT,
            relays TEXT,
            shippingzones TEXT NOT NULL,
            rating INTEGER DEFAULT 0
        );
    """
    )

    """
    Initial products table.
    """
    await db.execute(
        f"""
        CREATE TABLE market.products (
            id TEXT PRIMARY KEY,
            stall TEXT NOT NULL REFERENCES {db.references_schema}stalls (id) ON DELETE CASCADE,
            product TEXT NOT NULL,
            categories TEXT,
            description TEXT,
            image TEXT,
            price INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            rating INTEGER DEFAULT 0
        );
    """
    )

    """
    Initial zones table.
    """
    await db.execute(
        """
        CREATE TABLE market.zones (
            id TEXT PRIMARY KEY,
            "user" TEXT NOT NULL,
            cost TEXT NOT NULL,
            countries TEXT NOT NULL
        );
    """
    )

    """
    Initial orders table.
    """
    await db.execute(
        f"""
        CREATE TABLE market.orders (
            id {db.serial_primary_key},
            wallet TEXT NOT NULL,
            username TEXT,
            pubkey TEXT,
            shippingzone TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT NOT NULL,
            total INTEGER NOT NULL,
            invoiceid TEXT NOT NULL,
            paid BOOLEAN NOT NULL,
            shipped BOOLEAN NOT NULL,
            time TIMESTAMP NOT NULL DEFAULT """
        + db.timestamp_now
        + """
        );
    """
    )

    """
    Initial order details table.
    """
    await db.execute(
        f"""
        CREATE TABLE market.order_details (
            id TEXT PRIMARY KEY,
            order_id INTEGER NOT NULL REFERENCES {db.references_schema}orders (id) ON DELETE CASCADE,
            product_id TEXT NOT NULL REFERENCES {db.references_schema}products (id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL
        );
    """
    )

    """
    Initial market table.
    """
    await db.execute(
        """
        CREATE TABLE market.markets (
            id TEXT PRIMARY KEY,
            usr TEXT NOT NULL,
            name TEXT
        );
    """
    )

    """
    Initial market stalls table.
    """
    await db.execute(
        f"""
        CREATE TABLE market.market_stalls (
            id TEXT PRIMARY KEY,
            marketid TEXT NOT NULL REFERENCES {db.references_schema}markets (id) ON DELETE CASCADE,
            stallid TEXT NOT NULL REFERENCES {db.references_schema}stalls (id) ON DELETE CASCADE
        );
    """
    )

    """
    Initial chat messages table.
    """
    await db.execute(
        f"""
        CREATE TABLE market.messages (
            id {db.serial_primary_key},
            msg TEXT NOT NULL,
            pubkey TEXT NOT NULL,
            id_conversation TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT """
        + db.timestamp_now
        + """            
        );
    """
    )

    if db.type != "SQLITE":
        """
        Create indexes for message fetching
        """
        await db.execute(
            "CREATE INDEX idx_messages_timestamp ON market.messages (timestamp DESC)"
        )
        await db.execute(
            "CREATE INDEX idx_messages_conversations ON market.messages (id_conversation)"
        )


async def m002_add_custom_relays(db):
    """
    Add custom relays to stores
    """
    await db.execute("ALTER TABLE market.stalls ADD COLUMN crelays TEXT;")


async def m003_fiat_base_multiplier(db):
    """
    Store the multiplier for fiat prices. We store the price in cents and
    remember to multiply by 100 when we use it to convert to Dollars.
    """
    await db.execute(
        "ALTER TABLE market.stalls ADD COLUMN fiat_base_multiplier INTEGER DEFAULT 1;"
    )

    await db.execute(
        "UPDATE market.stalls SET fiat_base_multiplier = 100 WHERE NOT currency = 'sat';"
    )


async def m004_add_privkey_to_stalls(db):
    await db.execute("ALTER TABLE market.stalls ADD COLUMN privatekey TEXT")


async def m005_add_currency_to_zones(db):
    await db.execute("ALTER TABLE market.zones ADD COLUMN stall TEXT")
    await db.execute("ALTER TABLE market.zones ADD COLUMN currency TEXT DEFAULT 'sat'")


async def m006_delete_market_settings(db):
    await db.execute("DROP TABLE market.settings")


async def m007_order_id_to_UUID(db):
    """
    Migrate ID column type to string for UUIDs and migrate existing data
    """

    await db.execute("ALTER TABLE market.orders RENAME TO orders_old")
    await db.execute(
        f"""
        CREATE TABLE market.orders (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            username TEXT,
            pubkey TEXT,
            shippingzone TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT NOT NULL,
            total INTEGER NOT NULL,
            invoiceid TEXT NOT NULL,
            paid BOOLEAN NOT NULL,
            shipped BOOLEAN NOT NULL,
            time TIMESTAMP NOT NULL DEFAULT """
        + db.timestamp_now
        + """
        );
        """
    )

    for row in [
        list(row) for row in await db.fetchall("SELECT * FROM market.orders_old")
    ]:
        await db.execute(
            """
            INSERT INTO market.orders (
                id,
                wallet,
                username,
                pubkey,
                shippingzone,
                address,
                email,
                total,
                invoiceid,
                paid,
                shipped,
                time
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(row[0]),
                row[1],
                row[2],
                row[3],
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
                row[10],
                int(row[11]),
            ),
        )

    await db.execute("DROP TABLE market.orders_old")


async def m008_message_id_to_TEXT(db):
    """
    Migrate ID column type to string for UUIDs and migrate existing data
    """

    await db.execute("ALTER TABLE market.messages RENAME TO messages_old")
    await db.execute(
        f"""
        CREATE TABLE market.messages (
            id TEXT PRIMARY KEY,
            msg TEXT NOT NULL,
            pubkey TEXT NOT NULL,
            id_conversation TEXT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT """
        + db.timestamp_now
        + """            
        );
    """
    )

    for row in [
        list(row) for row in await db.fetchall("SELECT * FROM market.messages_old")
    ]:
        await db.execute(
            """
            INSERT INTO market.messages(
                id,
                msg,
                pubkey,
                id_conversation,
                timestamp
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(row[0]),
                row[1],
                row[2],
                row[3],
                int(row[4]),
            ),
        )

    await db.execute("DROP TABLE market.messages_old")
