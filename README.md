# AWS Image Cleanup Command Line Tool

Command line tool to deregister unused AMIs

## Getting Started

Clone this repository

Install dependencies: `$ pip3 install -r requirements.txt`

Set up a configuration file. Examples provided in `config.json.example` and `config.yml.example`

Make sure your aws credentials are set in your `~/.aws` directory

Run the command in PLAN mode with:

`$ python3 image_cleanup.py --config_file config.yml --plan`

Carefully review the output and make sure that you would like to deregister the listed AMIs

Run the command in EXECUTE mode with:

`$ python3 image_cleanup.py --config_file config.yml --execute`

Follow the prompts

## Configuration

Configuration files can be provided in either JSON or YAML format.
Examples are provided in `config.json.example` and `config.yml.example`.

### Configuration values:

**Required**

tags (type: dict): keys are tag names, values in tag values in list (tags to target for removal)

**Optional**

exclusion_tags (type: dict, default: None): keys are tag names, values in tag values in list (these are the tags to exclude from removal)

days_kept (type: int, default: 7): always keep images that are less than this many days old

iterations_retained (type: int, default: 3): allow this many iterations of an ami (based on name) to remain

excluded_ids (type: list, default: None): list of AMI IDs to leave in place

## Development

Install dependencies:

```
$ pip3 install -r requirements.txt
$ pip3 install -r requirements_dev.txt
```

Run unit tests:

`$ pytest -v`

Run code formatter:

```
$ black image_cleanup.py 
```