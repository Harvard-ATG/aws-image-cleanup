import argparse
import boto3
import json
import yaml

from utility_functions import (
    time_to_live,
    latest_images,
    parse_config_file,
    parse_tags,
)

parser = argparse.ArgumentParser(description="Deregister unused targeted AMIs")
parser.add_argument(
    "-c",
    "--config_file",
    nargs="?",
    type=argparse.FileType("r"),
    help="Configuration file for targeting AMIs",
    required=True,
)
parser.add_argument(
    "-p",
    "--plan",
    action="store_true",
    help="Provide output on exactly which AMIs will be deregistered",
)
parser.add_argument(
    "-e", "--execute", action="store_true", help="Execute the deregistering of AMIs"
)

args = parser.parse_args()


def handler(config, plan=True):

    boto_resource = boto3.resource("ec2")

    # parse the config file, so we don't need to check it everywhere
    configuration = parse_config_file(config)
    if configuration == False:
        return False

    if configuration["tags"] == "ALL":
        inclusion_filters = []
    else:
        inclusion_filters = parse_tags(configuration["tags"])
        if inclusion_filters == False:
            quit()

    # get all the images based on tags, that we own
    included_images = boto_resource.images.filter(
        Owners=["self"], Filters=inclusion_filters
    )

    # get a list of images that WE SHOULD NOT TOUCH
    # just in case they sneak in
    if configuration["exclusion_tags"] == "ALL":
        print("Exluding 'ALL' tags - meaning 'ALL' AMIs. Exiting.")
        quit()
    if configuration["exclusion_tags"]:
        exclusion_filters = parse_tags(configuration["exclusion_tags"])
        if exclusion_filters == False:
            quit()

        if exclusion_filters:
            exluded_images = boto_resource.images.filter(
                Owners=["self"], Filters=exclusion_filters
            )
        else:
            exluded_images = []
    else:
        exluded_images = []

    excluded_images_by_tags = [image.id for image in exluded_images]
    specificly_excluded_ids = configuration["excluded_ids"]
    images_in_use = [instance.image_id for instance in boto_resource.instances.all()]
    newest_images = latest_images(included_images, configuration["iterations_retained"])
    young_images = time_to_live(included_images, configuration["days_kept"])

    set_of_image_ids_to_exclude = set(
        excluded_images_by_tags
        + specificly_excluded_ids
        + images_in_use
        + newest_images
        + young_images
    )

    if plan == True:
        print("The following AMIs would be deregistered:")
        for image in included_images:
            if image.id not in set_of_image_ids_to_exclude:
                print(f"{image.id}  {image.name}  {image.creation_date}")

    if plan == False:
        print("The following AMIs WILL BE deregistered:")
        for image in included_images:
            if image.id not in set_of_image_ids_to_exclude:
                print(f"{image.id}  {image.name}  {image.creation_date}")
        second_confirmation = input(
            "Would you like to deregister the above AMIs? ['yes' to confirm]: "
        )
        if second_confirmation != "yes":
            print("Exiting.")
            return False
        else:
            for image in included_images:
                if image.id not in set_of_image_ids_to_exclude:
                    print(f"This is where I would image.deregister() for {image.id}")


f = args.config_file
file_extension = f.name.lower()

if file_extension.endswith(".json"):
    config = json.load(f)
elif file_extension.endswith(".yml") or file_extension.endswith(".yaml"):
    config = yaml.safe_load(f)
else:
    print(
        "The --config-file argument must be a json or yaml file, and have a .json .yml or .yaml file  extension"
    )
    quit()

if args.plan:
    print("Running in PLAN mode")
    handler(config, plan=True)
elif not args.execute and not args.plan:
    print("Please, specify if you would like to run --plan or --execute.")
    print("If you are unsure, run in PLAN mode with --plan")
    quit()
else:
    print("Running in EXECUTE mode")
    confirmation = input(
        "Are you sure you want to run in EXECUTE mode? ['yes' to confirm]: "
    )
    if confirmation != "yes":
        print("You can run this command with --plan to review the potential action.")
        quit()
    else:
        handler(config, plan=False)
