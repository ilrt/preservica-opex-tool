import boto3
import os
import argparse
import datetime
import sys
import configparser

parser = argparse.ArgumentParser(prog='upload',
                                 description='Tool to upload files to preservica')
parser.add_argument('-c', '--config', required=True, help='Config file')
parser.add_argument('-t', '--target', required=True, help='The folder used as the opex target')
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Explain what is happening')
parser.add_argument('-d', '--dry-run', action='store_true',
                    help="Don't actually perform any actions, for testing")

sys.argv.pop(0)  # why do I need this?
arguments = parser.parse_args(sys.argv)

# Open conf
config = configparser.ConfigParser()
config.read(arguments.config)

# get correct credentials for required bucket
ACCESS_KEY = config[args.bucket]['ACCESS_KEY']
SECRET_KEY = config[args.bucket]['SECRET_KEY']
BUCKET_NAME = config[args.bucket]['BUCKET_NAME']
OPEX_DIR = arguments.target
UPLOAD_BASE = os.path.basename(OPEX_DIR)

# function to parse line of instruction and upload
def upload_to_s3(instruction) -> None:
    print(instruction)
    file, target = instruction.split("\t")
    print(f'Uploading {os.path.basename(file)}')
    #s3.upload_file(file, BUCKET_NAME, Key= CONTAINER + target)


def sort_key(upload_entry):
    # Take the target path, e.g. /foo/bar/filename
    # and prefix opexes with ' ' to ensure they are uploaded first
    # (or '~' for last)
    target = upload_entry[1]
    if target.endswith('.opex'):
        return ' ' + target # bump opexes to top
    else:
        return target


# Load upload list
def load_uploads(dir, filename):
    upload_path = os.path.join(dir, filename)
    with open(upload_path, 'r') as uploads:
        upload_plan = [ line.strip().split("\t",2) for line in uploads ]
        return sorted(upload_plan, key=sort_key)


# Map upload plan to actual upload location with timestamp
def map_upload(dest, timestamp):
    if dest == '/root.opex':
        # Special case
        dest_real = dest.replace('root.opex', f"{UPLOAD_BASE}-{timestamp}.opex")
        return f"/{UPLOAD_BASE}-{timestamp}{dest_real}"
    else:
        return f"/{UPLOAD_BASE}-{timestamp}{dest}"

upload_plan = load_uploads(OPEX_DIR, 'to_upload.txt')

# We will use this to allow repeated uploads of the same material
# without overwriting
timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")

timestamped_upload_plan = [[i[0], map_upload(i[1], timestamp)] for i in upload_plan]

# Upload
s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)

for source, target in timestamped_upload_plan:
    print(f"Upload {source}\n\tto {BUCKET_NAME}\n\tas {target}")
    if not arguments.dry_run:
        s3_client.upload_file(source, BUCKET_NAME, target)

print(f"\nFinished. See {UPLOAD_BASE}-{timestamp} in {BUCKET_NAME}")
