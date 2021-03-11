import argparse
import boto3
import json
import yaml
import os
from datetime import timedelta
from dateutil import parser

EXCLUSION_TAGS = os.environ.get('EXCLUSION_TAGS', '')
TAGS = os.environ.get('TAGS', '')
UNUSED_IMAGE_DAYS_KEPT = os.environ.get('UNUSED_IMAGE_DAYS_KEPT', 7)
REGION = os.environ.get('REGION', 'us-east-1')
EXCLUSION_IDS = os.environ.get('EXCLUSION_IDS', '')

# TODO POSSIBLY MOVE AMI TO S3 -> for backup

parser = argparse.ArgumentParser(description='Deregister unused targeted AMIs')
parser.add_argument('-c','--config_file', nargs='?', type=argparse.FileType('r'),
    help='Configuration file for targeting AMIs', required=True)
parser.add_argument('-p', '--plan', action='store_true',
    help='Provide output on exactly which AMIs will be deregistered')
parser.add_argument('-e', '--execute', action='store_true',
    help='Execute the deregistering of AMIs')

args = parser.parse_args()


def parse_tags(tags):
    try:
        tag_filters = [ {'Name': f"tag:{tag}", 'Values': tags[tag]} for tag in tags.keys() ]
        return tag_filters
    except AttributeError:
        print("Tags not formatted correctly in configuration file")
        quit()

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

    # TODO what if iterations_allowed is 0

    images_by_name = {}
    for image in images:
        # TODO make sure that I am checking all available types of ami naming conventions
        split_name = image.name.split('-')
        filtered_name = filter(not_int, split_name)
        joined_name = "-".join(filtered_name)
        image_date_created = parser.parse(image.creation_date, ignoretz=True)

        if joined_name not in images_by_name.keys():
            images_by_name[joined_name] = [(image.id, image_date_created)]
        elif len(images_by_name[joined_name]) < iterations_allowed:
            images_by_name[joined_name].append(((image.id, image_date_created)))
        elif len(images_by_name[joined_name]) >= iterations_allowed:
            # sort the list of tuples based on second tuple value oldest to newest
            images_by_name[joined_name].sort(key = lambda x: x[1])
            # if this image is newer than the oldest image in the list
            if image_date_created > images_by_name[joined_name][0][1]:
                images_by_name[joined_name].pop(0) # remove the older one
                images_by_name[joined_name].append((image.id, image_date_created)) # append this image

    # we dont actually need the created_date or the supposed image names
    # so just return a list of IDs            
    return [ tup[0] for name in images_by_name for tup in images_by_name[name] ]

def parse_config_file(config):
    # check that tags is specified
    # All other configurations may take a defualt value
    configuration = {}
    try:
        configuration['tags'] = config['tags']
    except KeyError:
        print("'tags' must be specified in the configuration file.")
        print("If you would like all the possible AMIs to be included, you may set 'tags': 'ALL'")
        print("Otherwise, you must provide tags to filter for the AMIs that you want to deregister.")
        return False

    configuration['exclusion_tags'] = config.get('exclusion_tags', None)
    configuration['days_kept'] = config.get('days_kept', 7)
    configuration['iterations_retained'] = config.get('iterations_retained', 3)
    configuration['excluded_ids'] = config.get('excluded_ids', [])

    return configuration
    

def handler(config, plan=True):

    client = boto3.resource("ec2")

    # perhaps I should parse the config so I dont need to check it everywhere
    configuration = parse_config_file(config)
    if configuration == False:
        return False

    if configuration['tags'] == "ALL":
        inclusion_filters = []
    else:
        inclusion_filters = parse_tags(configuration['tags'])

    # get all the images based on tags, that we own
    included_images = client.images.filter(
        Owners=['self'],
        Filters=inclusion_filters
    )

    # get a list of images that WE SHOULD NOT TOUCH
    # just in case they sneak in 
    # TODO check that configuration['exclusion_tags'] len() > 0
    # TODO maybe the exclusion should also allow for "ALL" although it doesn't make mucch sense
    if configuration['exclusion_tags']:
        exclusion_filters = parse_tags(configuration['exclusion_tags'])
        if exclusion_filters:
            exluded_images = client.images.filter(
                Owners=['self'],
                Filters=exclusion_filters
            )
        else:
            exluded_images = []

    excluded_images_by_tags = [ image.id for image in exluded_images ]
    specificly_excluded_ids = configuration['excluded_ids']
    images_in_use = [instance.image_id for instance in client.instances.all()] # TODO check that this isnt just running instances
    newest_images = latest_images(included_images, configuration['iterations_retained'])
    young_images = time_to_live(included_images, configuration['days_kept'])
    # TODO check if there is pagination

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
        second_confirmation = input("Would you like to deregister the above AMIs? ['yes' to confirm]: ")
        if second_confirmation != 'yes':
            print("Exiting.")
            return False
        else:
            for image in included_images:
                if image.id not in set_of_image_ids_to_exclude:
                    print(f"This is where I would image.deregister() for {image.id}")


f = args.config_file
file_extension = f.name.lower()

if file_extension.endswith('.json'):
    config = json.load(f)
elif (file_extension.endswith('.yml') or file_extension.endswith('.yaml')):
    config = yaml.safe_load(f)
else:
    print("The --config-file argument must be a json or yaml file, and have a .json .yml or .yaml file  extension")
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
    confirmation = input("Are you sure you want to run in EXECUTE mode? ['yes' to confirm]: ")
        if confirmation != 'yes':
            print("You can run this command with --plan to review the potential action.")
            quit()
        else:
            handler(config, plan=False)

