var sentry_dsn = document.documentElement.getAttribute('data-sentry-dsn');
Sentry.init({dsn: sentry_dsn});
