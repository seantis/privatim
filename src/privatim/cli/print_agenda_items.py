from __future__ import annotations
import click
from pyramid.paster import bootstrap
from pyramid.paster import get_appsettings
from sqlalchemy import select
from privatim.models import Meeting
from privatim.orm import get_engine, Base


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from privatim.models import AgendaItem


DEFAULT_MEETING_ID = '359d71d2-2162-4110-b021-a0239f7a3236'


@click.command()
@click.argument('config_uri')
@click.option(
    '--meeting-id', default=DEFAULT_MEETING_ID, help='Meeting ID to analyze'
)
def main(config_uri: str, meeting_id: str) -> None:
    """Analyze agenda items positions for a specific meeting."""
    env = bootstrap(config_uri)
    settings = get_appsettings(config_uri)
    engine = get_engine(settings)
    Base.metadata.create_all(engine)

    with env['request'].tm:
        session = env['request'].dbsession

        meeting = session.execute(
            select(Meeting).where(Meeting.id == meeting_id)
        ).scalar_one_or_none()

        if not meeting:
            print(f'Meeting with ID {meeting_id} not found')
            return
        if not meeting.agenda_items:
            print('\nNo agenda items found for this meeting')
            return

        print_agenda_items_positions(meeting.agenda_items)


def print_agenda_items_positions(items: list['AgendaItem']) -> None:
    """Print position and title of each agenda item."""
    for item in sorted(items, key=lambda x: x.position):
        print(f'{item.position}. {item.title}')


if __name__ == '__main__':
    main()
