import argparse
import boto3
import json
import sys
import yaml

from utility_functions import (
    deregister_loop,
    latest_images,
    parse_config_file,
    parse_tags,
    time_to_live,
    verbose_exclusion_loops,
)


def handler(config, plan=True, verbose=False):
    """
    Takes a config dict, plan bool, and verbose bool. Returns int (0,1) to mark pass or error.
    Side effects include printing image information, getting user input and deregistering images.
    """
    boto_resource = boto3.resource("ec2")

    # parse the config file, so we don't need to check it everywhere
    configuration = parse_config_file(config)
    if configuration == False:
        return 1

    if configuration["tags"] == "ALL":
        inclusion_filters = []
    else:
        inclusion_filters = parse_tags(configuration["tags"])
        if inclusion_filters == False:
            return 1

    # get all the images based on tags, that we own
    included_images = boto_resource.images.filter(
        Owners=["self"], Filters=inclusion_filters
    )

    # get a list of images that WE SHOULD NOT TOUCH
    # just in case they sneak in
    if configuration["exclusion_tags"] == "ALL":
        print("Exluding 'ALL' tags - meaning 'ALL' AMIs. Exiting.")
        return 1
    if configuration["exclusion_tags"]:
        exclusion_filters = parse_tags(configuration["exclusion_tags"])
        if exclusion_filters == False:
            return 1

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
        deregister_loop(included_images, set_of_image_ids_to_exclude, plan)
    else:
        print("The following AMIs WILL BE deregistered:")
        deregister_loop(included_images, set_of_image_ids_to_exclude, not plan)
        second_confirmation = input(
            "Would you like to deregister the above AMIs? ['yes' to confirm]: "
        )
        if second_confirmation != "yes":
            print("Exiting.")
            return 0
        else:
            deregister_loop(included_images, set_of_image_ids_to_exclude, plan)

    if verbose == True:
        exclusion_categories = [
            (excluded_images_by_tags, "'exclusion_tags' defined in the config"),
            (specificly_excluded_ids, "'excluded_ids' defined in the config"),
            (
                images_in_use,
                "'images_in_use' - images that are associated with an instance",
            ),
            (
                newest_images,
                "'newest_images' - images that fit within the 'iterations_retained' config",
            ),
            (
                young_images,
                "'young_images' - images that are newer than the 'days_kept' config",
            ),
        ]
        verbose_exclusion_loops(included_images, exclusion_categories)
    return 0


def main(argv=None):
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
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Provide output for AMIs that are being excluded",
    )

    args = parser.parse_args(argv)

    f = args.config_file
    file_extension = f.name.lower()

    if file_extension.endswith(".json"):
        config = json.load(f)
    elif file_extension.endswith(".yml") or file_extension.endswith(".yaml"):
        config = yaml.safe_load(f)
    else:
        print(
            "The --config-file argument must be a json or yaml file, and have a .json .yml or .yaml extension"
        )
        return 1

    if args.plan:
        print("Running in PLAN mode")
        return handler(config, plan=True, verbose=args.verbose)
    elif not args.execute and not args.plan:
        print("Please, specify if you would like to run --plan or --execute.")
        print("If you are unsure, run in PLAN mode with --plan")
        return 1
    else:
        print("Running in EXECUTE mode")
        confirmation = input(
            "Are you sure you want to run in EXECUTE mode? ['yes' to confirm]: "
        )
        if confirmation != "yes":
            print(
                "You can run this command with --plan to review the potential action."
            )
            return 0
        else:
            return handler(config, plan=False, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
