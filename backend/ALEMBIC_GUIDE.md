# Alembic Database Migration Guide

This guide explains how to use Alembic for database migrations in the Open Gov Access backend.

## Overview

Alembic is a database migration tool for SQLAlchemy. It allows you to:
- Track database schema changes over time
- Apply changes incrementally
- Roll back changes if needed
- Keep database schema in sync across environments

## Setup

Alembic has been configured for this project with the following structure:

```
backend/
├── alembic/                    # Alembic directory
│   ├── versions/              # Migration scripts
│   ├── env.py                 # Alembic environment configuration
│   ├── script.py.mako         # Template for new migrations
│   └── README                 # Alembic readme
├── alembic.ini                # Alembic configuration file
├── models/
│   └── database.py            # SQLAlchemy models
└── config.py                  # Application configuration
```

## Configuration

The Alembic configuration automatically reads the database URL from:
1. `DATABASE_URL` environment variable (if set)
2. `config.py` settings (fallback)

Default database URL: `postgresql://opengov:opengov@localhost:5432/open_gov_access`

## Common Commands

All Alembic commands should be run from the `backend/` directory using `uv run`:

### 1. Create a New Migration (Auto-generate)

Automatically detect changes in your models and create a migration:

```bash
cd backend
uv run alembic revision --autogenerate -m "Description of changes"
```

Example:
```bash
uv run alembic revision --autogenerate -m "Add email field to officials table"
```

**Note:** Always review the auto-generated migration file before applying it!

### 2. Create a New Migration (Manual)

Create an empty migration file to write custom SQL:

```bash
cd backend
uv run alembic revision -m "Description of changes"
```

### 3. Apply Migrations (Upgrade)

Apply all pending migrations:

```bash
cd backend
uv run alembic upgrade head
```

Apply migrations up to a specific revision:

```bash
uv run alembic upgrade <revision_id>
```

Apply one migration at a time:

```bash
uv run alembic upgrade +1
```

### 4. Rollback Migrations (Downgrade)

Rollback the last migration:

```bash
cd backend
uv run alembic downgrade -1
```

Rollback to a specific revision:

```bash
uv run alembic downgrade <revision_id>
```

Rollback all migrations:

```bash
uv run alembic downgrade base
```

### 5. View Migration History

Show current revision:

```bash
cd backend
uv run alembic current
```

Show migration history:

```bash
uv run alembic history
```

Show verbose history with details:

```bash
uv run alembic history --verbose
```

### 6. Generate SQL (Without Applying)

Generate SQL for migrations without applying them:

```bash
cd backend
uv run alembic upgrade head --sql
```

This is useful for reviewing changes or applying them manually.

## Workflow

### Making Schema Changes

1. **Modify your models** in `models/database.py`
   ```python
   # Example: Add a new field
   class Official(Base):
       # ... existing fields ...
       email = Column(String(255), nullable=True)
   ```

2. **Create a migration**
   ```bash
   cd backend
   uv run alembic revision --autogenerate -m "Add email to officials"
   ```

3. **Review the migration file**
   - Check `backend/alembic/versions/<timestamp>_<slug>.py`
   - Verify the `upgrade()` and `downgrade()` functions
   - Make any necessary adjustments

4. **Apply the migration**
   ```bash
   uv run alembic upgrade head
   ```

5. **Test the changes**
   - Verify the database schema
   - Test your application
   - If issues arise, rollback: `uv run alembic downgrade -1`

### Initial Database Setup

For a fresh database, you have two options:

**Option 1: Use Alembic migrations (Recommended)**
```bash
cd backend
uv run alembic upgrade head
```

**Option 2: Use the init_db function (Legacy)**
```bash
cd backend
uv run python main.py init --database postgresql://opengov:opengov@localhost:5432/open_gov_access
```

**Note:** Once you start using Alembic, stick with it for all schema changes.

## Migration File Structure

A typical migration file looks like this:

```python
"""Add email to officials

Revision ID: abc123def456
Revises: previous_revision_id
Create Date: 2025-11-08 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision: str = 'abc123def456'
down_revision: Union[str, Sequence[str], None] = 'previous_revision_id'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Apply the migration."""
    op.add_column('officials', sa.Column('email', sa.String(255), nullable=True))

def downgrade() -> None:
    """Rollback the migration."""
    op.drop_column('officials', 'email')
```

## Best Practices

1. **Always review auto-generated migrations** - Alembic might not catch everything correctly
2. **Test migrations in development first** - Never apply untested migrations to production
3. **Write reversible migrations** - Always implement both `upgrade()` and `downgrade()`
4. **Use descriptive migration messages** - Make it clear what each migration does
5. **One logical change per migration** - Don't bundle unrelated changes
6. **Backup before migrating production** - Always have a backup before applying migrations
7. **Version control your migrations** - Commit migration files to git
8. **Don't modify existing migrations** - Once applied, create a new migration instead

## Common Operations

### Adding a Column

```python
def upgrade() -> None:
    op.add_column('table_name', sa.Column('column_name', sa.String(255), nullable=True))

def downgrade() -> None:
    op.drop_column('table_name', 'column_name')
```

### Removing a Column

```python
def upgrade() -> None:
    op.drop_column('table_name', 'column_name')

def downgrade() -> None:
    op.add_column('table_name', sa.Column('column_name', sa.String(255), nullable=True))
```

### Adding an Index

```python
def upgrade() -> None:
    op.create_index('idx_table_column', 'table_name', ['column_name'])

def downgrade() -> None:
    op.drop_index('idx_table_column', 'table_name')
```

### Creating a Table

```python
def upgrade() -> None:
    op.create_table(
        'new_table',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

def downgrade() -> None:
    op.drop_table('new_table')
```

## Troubleshooting

### "Target database is not up to date"

This means there are pending migrations. Run:
```bash
uv run alembic upgrade head
```

### "Can't locate revision identified by 'xyz'"

The migration history is out of sync. Check:
1. Are all migration files present in `alembic/versions/`?
2. Is the database's `alembic_version` table correct?

### Database Permission Errors

**Error:** `psycopg2.errors.InsufficientPrivilege: permission denied for schema public`

This is common in PostgreSQL 15+ where default schema permissions changed.

**Solution 1 - Grant Permissions (Recommended):**
```bash
# Connect as postgres superuser
psql -U postgres -d open_gov_access << 'EOF'
GRANT ALL PRIVILEGES ON DATABASE open_gov_access TO opengov;
GRANT ALL PRIVILEGES ON SCHEMA public TO opengov;
ALTER SCHEMA public OWNER TO opengov;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO opengov;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO opengov;
EOF
```

**Solution 2 - Recreate Database:**
```bash
psql -U postgres -c "DROP DATABASE IF EXISTS open_gov_access;"
psql -U postgres -c "CREATE DATABASE open_gov_access OWNER opengov;"
```

**Solution 3 - Use Superuser Temporarily:**
```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/open_gov_access"
uv run alembic upgrade head
```

### Autogenerate Not Detecting Changes

1. Ensure models are imported in `alembic/env.py`
2. Check that `target_metadata = Base.metadata` is set correctly
3. Verify your models inherit from `Base`

## Environment Variables

Set these environment variables to customize database connection:

```bash
export DATABASE_URL="postgresql://user:password@host:port/database"
```

Or create a `.env` file in the `backend/` directory:

```
DATABASE_URL=postgresql://opengov:opengov@localhost:5432/open_gov_access
```

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

