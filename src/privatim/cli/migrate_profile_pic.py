import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings

from privatim.models import User
from privatim.models.profile_pic import get_or_create_default_profile_pic
from privatim.orm import get_engine, Base


@click.command()
@click.argument('config_uri')
def main(config_uri: str) -> None:

    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        dbsession = env['request'].dbsession

        # Update existing users and generate profile pics
        default_pic = get_or_create_default_profile_pic(dbsession)
        users = dbsession.query(User).all()
        for user in users:
            # Generate tags if not present
            if not user.tags:
                user.tags = (
                    user.first_name[:1] + user.last_name[:1]
                ).upper() or user.email[:2].upper()

            if (
                user.profile_pic is None or
                user.profile_pic.content == default_pic.content
                or user.profile_pic_id is None
            ):
                user.generate_profile_picture(dbsession)

        dbsession.flush()


if __name__ == '__main__':
    main()
