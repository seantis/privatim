# from tests.conftest import consultation
# from webob.multidict import MultiDict
#
# from privatim.forms.consultation_form import ConsultationForm
# from privatim.testing import DummyRequest
#
#
# def test_edit_consultation_form(consultation):
#
#     request = DummyRequest()
#     form = ConsultationForm(consultation, request)
#     assert not form.validate()
#
#     request = DummyRequest(post=MultiDict({
#         'consultation-form-title': consultation.title,
#         'consultation-form-description': consultation.description,
#         'consultation-form-comments': consultation.comments,
#         'consultation-form-recommendation': consultation.recommendation,
#         # 'consultation-form-status': consultation.status,
#     }))
#     form = ConsultationForm(consultation, request)
#     assert form.validate()
