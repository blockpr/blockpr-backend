import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

# Database connection pool
db_pool = None


async def init_db():
    """Initialize database connection pool"""
    global db_pool
    supabase_url = os.getenv("SUPABASE_URL")
    
    if not supabase_url:
        raise ValueError("SUPABASE_URL environment variable is not set")
    
    # Extract connection details from Supabase URL
    # Supabase URL format: postgresql://postgres:[password]@[host]:[port]/postgres
    db_pool = await asyncpg.create_pool(
        supabase_url,
        min_size=1,
        max_size=10,
    )
    print("Database connection pool created successfully")


async def close_db():
    """Close database pool on shutdown"""
    global db_pool
    if db_pool:
        await db_pool.close()
        print("Database connection pool closed")


def get_db_pool():
    """Get the database connection pool"""
    if db_pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return db_pool
