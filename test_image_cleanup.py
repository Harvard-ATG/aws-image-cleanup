from unittest.mock import patch, call

from utility_functions import (
    not_int,
    time_to_live,
    latest_images,
    parse_config_file,
    parse_tags,
    deregister_loop,
)


class ExampleImage:
    def __init__(self, amiId, creation_date, name):
        self.id = amiId
        self.creation_date = creation_date
        self.name = name


test_images = [
    (1, "May 1, 2020 at 10:19:24 AM UTC-4", "atg-test1-123423543"),
    (2, "May 2, 2020 at 10:19:24 AM UTC-4", "atg-test1-123423545"),
    (3, "May 3, 2020 at 10:19:24 AM UTC-4", "atg-test1-123423546"),
    (4, "May 1, 2020 at 10:19:24 AM UTC-4", "atg-test2-123423546"),
    (5, "May 2, 2020 at 10:19:24 AM UTC-4", "atg-test2-123423547"),
    (6, "May 1, 2020 at 10:19:24 AM UTC-4", "atg-test3-123423547"),
]


def test_not_int():
    assert not_int(1) == False
    assert not_int("1") == False
    assert not_int("ab123") == True


def test_time_to_live():
    test_images_iterable = [ExampleImage(im[0], im[1], im[2]) for im in test_images]
    assert time_to_live(test_images_iterable, 2) == []
    assert time_to_live(test_images_iterable, 100000) == [1, 2, 3, 4, 5, 6]


def test_latest_images():
    test_images_iterable = [ExampleImage(im[0], im[1], im[2]) for im in test_images]
    assert latest_images(test_images_iterable, 1) == [3, 5, 6]
    assert latest_images(test_images_iterable, 2) == [2, 3, 4, 5, 6]
    assert latest_images(test_images_iterable, 0) == []


def test_parse_config_file():
    full_config = {
        "tags": {
            "someTag": ["someValue", "anotherValue"],
            "anotherTag": ["correctValue"],
        },
        "exclusion_tags": {
            "something": ["someValue", "anotherValue"],
            "else": ["correctValue"],
        },
        "days_kept": 2,
        "iterations_retained": 1,
        "excluded_ids": ["an-amiId"],
    }
    configuration = parse_config_file(full_config)
    assert configuration["tags"] == full_config["tags"]
    assert configuration["exclusion_tags"] == full_config["exclusion_tags"]
    assert configuration["days_kept"] == full_config["days_kept"]
    assert configuration["iterations_retained"] == full_config["iterations_retained"]
    assert configuration["excluded_ids"] == full_config["excluded_ids"]

    partial_config = {
        "tags": {
            "someTag": ["someValue", "anotherValue"],
            "anotherTag": ["correctValue"],
        }
    }
    partial_configuration = parse_config_file(partial_config)
    assert partial_configuration["tags"] == partial_config["tags"]
    assert partial_configuration["exclusion_tags"] == None
    assert partial_configuration["days_kept"] == 7
    assert partial_configuration["iterations_retained"] == 3
    assert partial_configuration["excluded_ids"] == []

    # also check that passing an empty config will return False
    assert parse_config_file({}) == False


def test_parse_tags():
    correct_tags = {
        "someTag": ["someValue", "anotherValue"],
        "anotherTag": ["correctValue"],
    }
    bad_tags = {"sometag": "value"}
    expected_output = [
        {"Name": "tag:someTag", "Values": ["someValue", "anotherValue"]},
        {"Name": "tag:anotherTag", "Values": ["correctValue"]},
    ]
    assert parse_tags(correct_tags) == expected_output
    assert parse_tags(bad_tags) == False
    assert parse_tags([]) == False
    assert parse_tags({}) == False


@patch("builtins.print")
def test_deregister_loop(mocked_print):
    test_image = ExampleImage(
        1, "May 1, 2020 at 10:19:24 AM UTC-4", "atg-test1-123423543"
    )
    deregister_loop([test_image], [], True)  # "call" once
    deregister_loop([test_image], [], False)  # "call" again
    deregister_loop([test_image], [1], False)  # "call" again, but shouldn't do anything
    assert mocked_print.mock_calls == [
        call(
            "1  atg-test1-123423543  May 1, 2020 at 10:19:24 AM UTC-4"
        ),  # plan == True
        call("This is where I would image.deregister() for 1"),  # plan == False
    ]
