def flash(context, request):
    messages = request.session.pop_flash()
    if not messages:
        return ''

    return {
        'messages': messages
    }
