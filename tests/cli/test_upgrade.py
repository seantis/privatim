from privatim.cli.upgrade import UpgradeContext


def test_has_table(config):
    upgrade = UpgradeContext(config.dbsession)
    assert upgrade.has_table('consultations')
    assert not upgrade.has_table('bogus')


def test_drop_table(config):
    upgrade = UpgradeContext(config.dbsession)
    assert upgrade.has_table('meetings')
    assert upgrade.drop_table('meetings')
    assert not upgrade.has_table('meetings')
    assert not upgrade.drop_table('bogus')


def test_has_column(config):
    upgrade = UpgradeContext(config.dbsession)
    assert upgrade.has_column('meetings', 'id')
    assert not upgrade.has_column('meetings', 'bogus')
