from privatim.utils import flatten_comments
from tests.shared.utils import Bunch


class MockComment:
    def __init__(self, id, children=None):
        self.id = id
        self.children = children or []
        self.created = id  # Using id as a simple proxy for creation time


def mock_get_picture(comment, request):
    """ Just return something. This is not tested here."""
    return f"mock_picture_{comment.id}"


def test_flatten_comments_with_nesting():
    """
    input_comments:

    comment1
    └── comment2
        ├── comment3
        │   └── deep_nested
        └── comment2_child


    Expected output (flattened):

    comment1
    └───
        ├── comment2
        ├── comment3
        ├── deep_nested
        └── comment2_child
    """

    deep_nested = MockComment(4)
    comment3 = MockComment(3, [deep_nested])
    comment2_child = MockComment(5)
    comment2 = MockComment(2, [comment3, comment2_child])
    comment1 = MockComment(1, [comment2])
    input_comments = [comment1]
    request = Bunch()
    flattened = flatten_comments(
        input_comments, request, get_picture_for_comment=mock_get_picture
    )

    assert len(flattened) == 1
    assert len(flattened[0]['children']) == 4

    child_ids = [child['comment'].id for child in flattened[0]['children']]
    assert child_ids == [4, 3, 5, 2]

    for child in flattened[0]['children']:
        assert 'children' not in child  # Ensure no nested children


def test_empty_comments():
    comments = []
    request = Bunch()
    assert (
        flatten_comments(
            comments, request, get_picture_for_comment=mock_get_picture
        )
        == []
    )


def test_multiple_top_level_comments():
    comment1 = MockComment(1)
    comment2 = MockComment(2)

    request = Bunch()

    flattened = flatten_comments(
        [comment1, comment2], request, get_picture_for_comment=mock_get_picture
    )

    assert len(flattened) == 2
    assert flattened[0]['comment'].id == 1
    assert flattened[0]['picture'] == 'mock_picture_1'
    assert flattened[1]['comment'].id == 2
    assert flattened[1]['picture'] == 'mock_picture_2'
