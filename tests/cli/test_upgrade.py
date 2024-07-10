from privatim.cli.upgrade import UpgradeContext


def test_has_table(pg_config):
    upgrade = UpgradeContext(pg_config.dbsession)
    assert upgrade.has_table('consultations')
    assert not upgrade.has_table('bogus')


def test_has_column(pg_config):
    upgrade = UpgradeContext(pg_config.dbsession)
    assert upgrade.has_column('meetings', 'id')
    assert not upgrade.has_column('meetings', 'bogus')
