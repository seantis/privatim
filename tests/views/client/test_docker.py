def test_postgres_docker(postgresql):
    """Run test."""
    with postgresql.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
