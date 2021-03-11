from datetime import datetime, timedelta
from dateutil import parser


def not_int(val):
    try:
        int(val)
    except ValueError:
        return True
    return False


def time_to_live(images, days_to_live):
    # returns a list of image IDs
    return_list = []
    for image in images:
        image_date_created = parser.parse(image.creation_date, ignoretz=True)
        if image_date_created > datetime.now() - timedelta(days_to_live):
            return_list.append(image.id)
    return return_list


def latest_images(images, iterations_allowed):
    # returns a dict of tuples
    # returns:
    # {
    #     'one-image-name' : [(image.id, created_date), (image.id, created_date)],
    #     'another-image-name' : [(image.id, created_date)]
    # }

    if iterations_allowed == 0:
        return []

    images_by_name = {}
    for image in images:
        # TODO make sure that I am checking all available types of ami naming conventions
        split_name = image.name.split("-")
        filtered_name = filter(not_int, split_name)
        joined_name = "-".join(filtered_name)
        image_date_created = parser.parse(image.creation_date, ignoretz=True)

        if joined_name not in images_by_name.keys():
            images_by_name[joined_name] = [(image.id, image_date_created)]
        elif len(images_by_name[joined_name]) < iterations_allowed:
            images_by_name[joined_name].append(((image.id, image_date_created)))
        elif len(images_by_name[joined_name]) >= iterations_allowed:
            # sort the list of tuples based on second tuple value oldest to newest
            images_by_name[joined_name].sort(key=lambda x: x[1])
            # if this image is newer than the oldest image in the list
            if image_date_created > images_by_name[joined_name][0][1]:
                images_by_name[joined_name].pop(0)  # remove the older one
                images_by_name[joined_name].append(
                    (image.id, image_date_created)
                )  # append this image

    # we dont actually need the created_date or the supposed image names
    # so just return a list of IDs
    return [tup[0] for name in images_by_name for tup in images_by_name[name]]


def parse_config_file(config):
    # check that tags is specified
    # All other configurations may take a defualt value
    configuration = {}
    try:
        configuration["tags"] = config["tags"]
    except KeyError:
        print("'tags' must be specified in the configuration file.")
        print(
            "If you would like all the possible AMIs to be included, you may set 'tags': 'ALL'"
        )
        print(
            "Otherwise, you must provide tags to filter for the AMIs that you want to deregister."
        )
        return False

    configuration["exclusion_tags"] = config.get("exclusion_tags", None)
    configuration["days_kept"] = config.get("days_kept", 7)
    configuration["iterations_retained"] = config.get("iterations_retained", 3)
    configuration["excluded_ids"] = config.get("excluded_ids", [])

    return configuration


def parse_tags(tags):
    try:
        tag_filters = [
            {"Name": f"tag:{tag}", "Values": tags[tag]} for tag in tags.keys()
        ]
        for filter in tag_filters:
            if not isinstance(filter["Values"], list):
                print("Tag values must be list")
                return False
        return tag_filters
    except AttributeError:
        print("Tags not formatted correctly in configuration file")
        return False
