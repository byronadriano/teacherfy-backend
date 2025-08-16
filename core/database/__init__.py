# core/database/__init__.py
from .database import (
    get_db_connection,
    get_db_cursor,
    test_connection,
    get_user_by_email,
    create_user,
    log_user_login,
    log_user_activity,
    get_example_outline,
    save_example_outline,
)
from .usage import (
    check_user_limits,
    increment_usage,
)
