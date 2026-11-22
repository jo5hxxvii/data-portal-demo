import pytest

from portal.query_guard import check

OK = [
    "SELECT txn_id, amount FROM transactions WHERE amount > 100",
    "SELECT COUNT(*) FROM customers",
    "SELECT * FROM transactions LIMIT 5",
    "SELECT customer_id, name FROM customers;",
    "WITH big AS (SELECT * FROM transactions WHERE amount > 5000) SELECT COUNT(*) FROM big",
    "SELECT t.txn_id, c.name FROM transactions t JOIN customers c ON c.customer_id = t.customer_id",
]

BLOCKED = [
    "",
    "SELECT 1; DROP TABLE users",
    "SELECT 1; SELECT 2",
    "DROP TABLE customers",
    "DELETE FROM transactions",
    "UPDATE wallets SET balance = 0",
    "INSERT INTO customers (customer_id) VALUES ('x')",
    "SELECT email FROM customers",
    "SELECT c.email FROM customers c",
    "SELECT x FROM (SELECT email AS x FROM customers)",
    '"SELECT" ',
    "SELECT \"EMAIL\" FROM customers",
    "SELECT * FROM customers",
    "SELECT c.* FROM customers c",
    "SELECT * FROM (SELECT * FROM customers)",
    "WITH c AS (SELECT * FROM customers) SELECT 1 FROM c",
    "SELECT * FROM users",
    "SELECT password_hash FROM users",
    "SELECT * FROM audit_log",
    "SELECT * FROM sqlite_master",
    "SELECT * FROM main.transactions",
    "SELECT * FROM pragma_table_info('users')",
    "SELECT load_extension('x')",
    "SELECT readfile('/etc/passwd')",
    "PRAGMA table_info(users)",
    "SELECT * INTO newtable FROM transactions",
    "WITH x AS (DELETE FROM transactions RETURNING *) SELECT * FROM x",
]


@pytest.mark.parametrize("sql", OK)
def test_allowed(sql):
    assert check(sql) is None


@pytest.mark.parametrize("sql", BLOCKED)
def test_blocked(sql):
    assert check(sql) is not None
