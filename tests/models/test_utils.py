from datetime import datetime

from privatim.models.commentable import Comment
from privatim.utils import flatten_comments
from privatim.views.consultations import trim_filename


def test_empty_comments():
    comments = []
    assert flatten_comments(comments) == []


def test_single_level_comments():
    child1 = Comment(
        id="child1",
        content="Child 1",
        user_id="user2",
        parent_id="root",
        created=datetime(2023, 1, 2),
    )
    child2 = Comment(
        id="child2",
        content="Child 2",
        user_id="user3",
        parent_id="root",
        created=datetime(2023, 1, 1),
    )
    root = Comment(
        id="root",
        content="Root",
        user_id="user1",
        children=[child1, child2],
        created=datetime(2023, 1, 1),
    )
    comments = [root]
    assert flatten_comments(comments) == [
        {'comment': root, 'children': [child2, child1]}
    ]


def test_multiple_top_level_comments():
    child1 = Comment(
        id="child1",
        content="Child 1",
        user_id="user2",
        parent_id="root1",
        created=datetime(2023, 1, 2),
    )
    child2 = Comment(
        id="child2",
        content="Child 2",
        user_id="user3",
        parent_id="root1",
        created=datetime(2023, 1, 1),
    )
    root1 = Comment(
        id="root1",
        content="Root 1",
        user_id="user1",
        children=[child1, child2],
        created=datetime(2023, 1, 1),
    )
    root2 = Comment(
        id="root2",
        content="Root 2",
        user_id="user4",
        created=datetime(2023, 1, 3),
    )
    comments = [root1, root2]
    assert flatten_comments(comments) == [
        {'comment': root1, 'children': [child2, child1]},
        {'comment': root2, 'children': []},
    ]


def test_multiple_levels_of_nesting():
    grandchild1 = Comment(
        id="grandchild1",
        content="Grandchild 1",
        user_id="user4",
        parent_id="child1",
        created=datetime(2023, 1, 4),
    )
    child1 = Comment(
        id="child1",
        content="Child 1",
        user_id="user2",
        parent_id="root",
        children=[grandchild1],
        created=datetime(2023, 1, 2),
    )
    child2 = Comment(
        id="child2",
        content="Child 2",
        user_id="user3",
        parent_id="root",
        created=datetime(2023, 1, 1),
    )
    root = Comment(
        id="root",
        content="Root",
        user_id="user1",
        children=[child1, child2],
        created=datetime(2023, 1, 1),
    )
    comments = [root]
    assert flatten_comments(comments) == [
        {'comment': root, 'children': [child2, child1]}
    ]


def test_multiple_levels_of_nesting_with_multiple_children():
    greatgrandchild1 = Comment(
        id="greatgrandchild1",
        content="Great Grandchild 1",
        user_id="user6",
        parent_id="grandchild1",
        created=datetime(2023, 1, 6),
    )
    grandchild1 = Comment(
        id="grandchild1",
        content="Grandchild 1",
        user_id="user4",
        parent_id="child1",
        children=[greatgrandchild1],
        created=datetime(2023, 1, 4),
    )
    grandchild2 = Comment(
        id="grandchild2",
        content="Grandchild 2",
        user_id="user5",
        parent_id="child1",
        created=datetime(2023, 1, 5),
    )
    child1 = Comment(
        id="child1",
        content="Child 1",
        user_id="user2",
        parent_id="root",
        children=[grandchild1, grandchild2],
        created=datetime(2023, 1, 2),
    )
    child2 = Comment(
        id="child2",
        content="Child 2",
        user_id="user3",
        parent_id="root",
        created=datetime(2023, 1, 1),
    )
    root = Comment(
        id="root",
        content="Root",
        user_id="user1",
        children=[child1, child2],
        created=datetime(2023, 1, 1),
    )
    comments = [root]
    assert flatten_comments(comments) == [
        {'comment': root, 'children': [child2, child1]}
    ]


def test_multiple_top_level_comments_with_nesting():
    grandchild1 = Comment(
        id="grandchild1",
        content="Grandchild 1",
        user_id="user5",
        parent_id="child1",
        created=datetime(2023, 1, 4),
    )
    child1 = Comment(
        id="child1",
        content="Child 1",
        user_id="user2",
        parent_id="root1",
        children=[grandchild1],
        created=datetime(2023, 1, 2),
    )
    child2 = Comment(
        id="child2",
        content="Child 2",
        user_id="user3",
        parent_id="root1",
        created=datetime(2023, 1, 1),
    )
    root1 = Comment(
        id="root1",
        content="Root 1",
        user_id="user1",
        children=[child1, child2],
        created=datetime(2023, 1, 1),
    )
    child3 = Comment(
        id="child3",
        content="Child 3",
        user_id="user4",
        parent_id="root2",
        created=datetime(2023, 1, 3),
    )
    root2 = Comment(
        id="root2",
        content="Root 2",
        user_id="user4",
        children=[child3],
        created=datetime(2023, 1, 3),
    )
    comments = [root1, root2]
    assert flatten_comments(comments) == [
        {'comment': root1, 'children': [child2, child1]},
        {'comment': root2, 'children': [child3]},
    ]


def test_short_filename():
    filename = "short.txt"
    expected_output = "short.txt"
    assert trim_filename(filename) == expected_output


def test_long_filename():
    filename = "this_is_a_very_long_filename_that_exceeds_32_chars.txt"
    expected_output = "this_is_a_very_long_filen...txt"
    assert trim_filename(filename) == expected_output


def test_no_extension():
    filename = "filename_without_extension"
    expected_output = "filename_without_extension"
    assert trim_filename(filename) == expected_output


def test_empty_filename():
    filename = ""
    expected_output = ""
    assert trim_filename(filename) == expected_output


def test_filename_with_dots():
    filename = "file.name.with.dots.txt"
    expected_output = "file.name.with.dots.txt"
    assert trim_filename(filename) == expected_output


def test_filename_with_exactly_32_chars():
    filename = "exactly_32_characters_long.txt"
    expected_output = "exactly_32_characters_long.txt"
    assert trim_filename(filename) == expected_output
