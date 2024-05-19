var sentry_dsn = document.documentElement.getAttribute('data-sentry_dsn');
Sentry.init({dsn: sentry_dsn});
