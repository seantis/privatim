import pytest
from webob.multidict import MultiDict

from privatim.models.utils import get_docx_text
from privatim.utils import attendance_status


def test_analyze_docx(sample_docx_file):
    docx_txt = get_docx_text(sample_docx_file)
    assert 'Simone Felbers iheimisch' in docx_txt
    assert 'Standup Philosophy & Drums' in docx_txt
    assert 'Ich habe Interesse an 2 Tickets:' in docx_txt
    assert 'Sa 18.01.' in docx_txt


@pytest.fixture
def sample_meeting_form():
    return MultiDict(
        [
            ('csrf_token', 'e9af8a15fbf97fcba639d2c09d5049917e66e7ed'),
            ('name', 'meeting name'),
            ('time', '1111-11-11T11:11'),
            ('attendees', 'ca258718-35bc-42a0-803d-13497fcb3639'),
            ('attendees', '27f1203f-a3a8-418f-89a2-41f0a2fbbd86'),
            ('attendance-2-user_id', 'ca258718-35bc-42a0-803d-13497fcb3639'),
            ('attendance-3-user_id', '27f1203f-a3a8-418f-89a2-41f0a2fbbd86'),
            ('attendance-3-status', 'y'),
        ]
    )


def test_user_with_status(sample_meeting_form):
    assert (
        attendance_status(
            sample_meeting_form, '27f1203f-a3a8-418f-89a2-41f0a2fbbd86'
        )
        is True
    )


def test_user_without_status(sample_meeting_form):
    assert (
        attendance_status(
            sample_meeting_form, 'ca258718-35bc-42a0-803d-13497fcb3639'
        )
        is False
    )


def test_nonexistent_user(sample_meeting_form):
    assert attendance_status(sample_meeting_form, 'non-existent-id') is False


def test_empty_multidict():
    empty_data = MultiDict()
    assert attendance_status(empty_data, 'any-id') is False


def test_user_with_multiple_entries(sample_meeting_form):
    sample_meeting_form.add(
        'attendance-4-user_id', '27f1203f-a3a8-418f-89a2-41f0a2fbbd86'
    )
    sample_meeting_form.add('attendance-4-status', 'n')
    assert (
        attendance_status(
            sample_meeting_form, '27f1203f-a3a8-418f-89a2-41f0a2fbbd86'
        )
        is True
    )


@pytest.fixture
def complex_meeting_form():
    return MultiDict(
        [
            ('csrf_token', 'e9af8a15fbf97fcba639d2c09d5049917e66e7ed'),
            ('name', 'sc'),
            ('time', '1111-11-11T11:11'),
            ('attendees', 'user1'),
            ('attendees', 'user2'),
            ('attendees', 'user3'),
            ('attendees', 'user4'),
            ('attendance-1-user_id', 'user1'),
            ('attendance-1-status', 'y'),
            ('attendance-2-user_id', 'user2'),
            ('attendance-2-status', 'n'),
            ('attendance-3-user_id', 'user3'),
            ('attendance-3-status', 'y'),
            ('attendance-4-user_id', 'user1'),
            ('attendance-4-status', 'n'),
            ('attendance-5-user_id', 'user3'),
            ('attendance-5-status', 'n'),
            ('attendance-6-user_id', 'user4'),
        ]
    )


def test_user_with_single_y_status(complex_meeting_form):
    assert attendance_status(complex_meeting_form, 'user1') is True


def test_user_with_only_n_status(complex_meeting_form):
    assert attendance_status(complex_meeting_form, 'user2') is False


def test_user_with_multiple_statuses_including_y(complex_meeting_form):
    assert attendance_status(complex_meeting_form, 'user3') is True


def test_user_with_multiple_entries_y_first(complex_meeting_form):
    complex_meeting_form.add('attendance-7-user_id', 'user2')
    complex_meeting_form.add('attendance-7-status', 'y')
    assert attendance_status(complex_meeting_form, 'user2') is True


def test_user_with_multiple_entries_y_last():
    data = MultiDict(
        [
            ('attendance-1-user_id', 'test-user'),
            ('attendance-1-status', 'n'),
            ('attendance-2-user_id', 'test-user'),
            ('attendance-2-status', 'n'),
            ('attendance-3-user_id', 'test-user'),
            ('attendance-3-status', 'y'),
        ]
    )
    assert attendance_status(data, 'test-user') is True


def test_user_with_multiple_entries_no_y():
    data = MultiDict(
        [
            ('attendance-1-user_id', 'test-user'),
            ('attendance-1-status', 'n'),
            ('attendance-2-user_id', 'test-user'),
            ('attendance-2-status', 'n'),
            ('attendance-3-user_id', 'test-user'),
        ]
    )
    assert attendance_status(data, 'test-user') is False


def test_multidict_with_only_user_ids():
    data = MultiDict(
        [
            ('attendance-1-user_id', 'user1'),
            ('attendance-2-user_id', 'user2'),
            ('attendance-3-user_id', 'user3'),
        ]
    )
    assert attendance_status(data, 'user1') is False
    assert attendance_status(data, 'user2') is False
    assert attendance_status(data, 'user3') is False
