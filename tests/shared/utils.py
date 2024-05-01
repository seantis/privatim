def find_login_form(resp_forms):
    """ More than one form exists on the login page. Find the one we need"""
    for form in resp_forms.values():
        if 'email' in form.fields and 'password' in form.fields:
            return form
    return None