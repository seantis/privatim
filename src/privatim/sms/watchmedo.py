from __future__ import annotations
from daemons import daemonizer  # type:ignore[import-untyped]
from watchdog.watchmedo import cli

cli.add_argument(
    '--pidfile',
    dest='pidfile',
    default='watchmedo.pid',
    help='path to pid file to be used for daemon'
)


def daemon() -> None:
    args = cli.parse_args()

    @daemonizer.run(pidfile=args.pidfile)
    def dispatcher() -> None:
        args.func(args)

    dispatcher()
