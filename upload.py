import boto3
import os
import argparse
import datetime
import sys
import configparser

parser = argparse.ArgumentParser(prog='upload',
                                 description='Tool to upload files to preservica')
parser.add_argument('--config', help='Config file (default ~/S3.ini)', default='~/S3.ini')
parser.add_argument('-t', '--target', required=True, help='The folder containing the opex files')
parser.add_argument('-b', '--bucket', required=True, help="Bucket (defined in config file)")
parser.add_argument('-c', '--container', required=True, help="Container to upload to")
parser.add_argument('-v', '--verbose', action='store_true',
                    help='Explain what is happening')
parser.add_argument('-d', '--dry-run', action='store_true',
                    help="Don't actually perform any actions, for testing")

sys.argv.pop(0)  # why do I need this?
args = parser.parse_args(sys.argv)

# Open conf
config = configparser.ConfigParser()
config.read(os.path.expanduser(args.config))

# get correct credentials for required bucket
ACCESS_KEY = config[args.bucket]['ACCESS_KEY']
SECRET_KEY = config[args.bucket]['SECRET_KEY']
BUCKET_NAME = config[args.bucket]['BUCKET_NAME']
OPEX_DIR = args.target
UPLOAD_BASE = os.path.basename(OPEX_DIR)

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
def map_upload(dest, container, base, timestamp):
    dir = f"{base}-{timestamp}"  # Dir for this particular upload
    if dest == '/root.opex':
        # Special case
        dest = dest.replace('root.opex', f"{dir}.opex")

    return f"{container}/{dir}{dest}"

upload_plan = load_uploads(OPEX_DIR, 'to_upload.txt')

# We will use this to allow repeated uploads of the same material
# without overwriting
timestamp = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M")

timestamped_upload_plan = [
    [i[0], map_upload(i[1], args.container, UPLOAD_BASE, timestamp)]
    for i in upload_plan]

# Upload
s3_client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)

for source, target in timestamped_upload_plan:
    print(f"Upload {source}\n\tto {BUCKET_NAME}\n\tas {target}")
    if not args.dry_run:
        s3_client.upload_file(source, BUCKET_NAME, target)

print(f"\nFinished. See {UPLOAD_BASE}-{timestamp} in {BUCKET_NAME}/{args.container}")
