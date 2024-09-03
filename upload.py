import boto3
import os
import configparser 
import argparse
import conf_wf

OPEX_DIR = conf_wf.working_dir

# TODO - declare in config file 
CONTAINER = 'opex_wildfilm'

# argeparse to get PUT or OPEX from CLI argument
parser = argparse.ArgumentParser(usage="Specifiy either PUT or OPEX as argument - eg. 'python3 upload.py PUT' " )
parser.add_argument('bucket', choices=['OPEX', 'PUT'], help="Specifiy either PUT or OPEX as argument - eg. 'python3 upload.py PUT' ")
args = parser.parse_args()

# fetch S3 credentials from config file
config = configparser.ConfigParser()
config.read(os.path.expanduser('~') + '/S3.ini')

# get correct credentials for required bucket
ACCESS_KEY = config[args.bucket]['ACCESS_KEY']
SECRET_KEY = config[args.bucket]['SECRET_KEY']
BUCKET_NAME = config[args.bucket]['BUCKET_NAME']

# setup s3 client for upload
s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)

# setup S3 bucket session to check structure after upload
sesssion = boto3.Session(aws_access_key_id=config[args.bucket]['ACCESS_KEY'], aws_secret_access_key=config[args.bucket]['SECRET_KEY'])
s3_session = sesssion.resource('s3')
bucket = s3_session.Bucket(config[args.bucket]['BUCKET_NAME'])

# function to parse line of instruction and upload  
def upload_to_s3(instruction) -> None:
    print(instruction)
    file, target = instruction.split("\t")
    print(f'Uploading {os.path.basename(file)}')
    s3.upload_file(file, BUCKET_NAME, Key= CONTAINER + target)

# Parse output from to_opex.py as text file
with open('to_upload.txt', 'r') as instructions: instructions = {os.path.basename(line.strip().split()[0]): line.strip() for line in instructions}
#print(instructions)
# Fetch opex files from 'working' directory - sort in correct order 
opex_files = os.listdir(OPEX_DIR)
opex_files.sort(reverse=True)

# upload opex file, with content following where present 
for opex_file in opex_files:
    upload_to_s3(instructions[opex_file])
    if len(opex_file.split('.')) > 2: # Looks for nested file extenstion in opex file name 
        upload_to_s3(instructions[opex_file.strip('.opex')])  # Fetch content path from dict


# Check bucket - print tree of new upload
