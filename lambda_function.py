'''
Elasticsearch Index Clean - Cleans up old index's according to retention
dates specified in config. This lambda function is triggered by an AWS cron event

Author: Jason Witting
Version: 0.1

Copyright (c) 2016 Jason Witting

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED
, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
'''
import json
from datetime import datetime, timedelta

import boto3
from elasticsearch import Elasticsearch, RequestsHttpConnection
from aws_requests_auth.aws_auth import AWSRequestsAuth

# config_bucket='lambda-cf-es-config'
CONFIG_BUCKET = 'lambda-elasticsearch-index-clean-config'
# config s3 location and filename
CONFIG_FILE = 'config.json'


def sts_auth(config):
    '''Genarate auth request to connect AWS ES with STS'''
    sts = boto3.client('sts')

    creds = sts.assume_role(
        RoleArn=config['sts_role_arn'],
        RoleSessionName=config['sts_session_name'])

    auth = AWSRequestsAuth(
        aws_access_key=creds['Credentials']['AccessKeyId'],
        aws_secret_access_key=creds[
            'Credentials']['SecretAccessKey'],
        aws_host=config['es_host'],
        aws_region=config['es_region'],
        aws_service='es',
        aws_token=creds['Credentials']['SessionToken']
    )
    return auth


def load_config(context):
    '''Load config file from S3 based on function alias'''
    config = ''

    # Check version
    function_name = context.function_name
    alias = context.invoked_function_arn.split(':').pop()

    if function_name == alias:
        alias = '$LATEST'
        print "No Version Set - Default to $LATEST"

    s3_client = boto3.client('s3')

    # set the file path
    file_path = '/tmp/config.json'

    # download the gzip log from s3
    s3_client.download_file(CONFIG_BUCKET, alias +
                            "/" + CONFIG_FILE, file_path)

    with open(file_path) as data:
        config = json.load(data)

    print "Succesfully loaded config file"
    return config


def get_index_list(es_client):
    '''returns a list of all elasticsearch indexes as JSON'''
    return json.loads(json.dumps(es_client.indices.get(index='_all')))


def delete_index(es_client, index_name):
    '''deletes a index specified as a string '''
    es_client.indices.delete(index=index_name)


def get_oldest_index(config, index_list):
    '''
    returns the oldest index name by date set in config. The index list
    is filtered by string set in the function config. If not match is found
    a None type is returned
    '''
    age = config['expiry-age']
    filtered_list = [s for s in index_list if config['string-match'] in s]
    comparison_date = datetime.today() - timedelta(days=int(age))

    for index in filtered_list:
        idx_creation_date = index_list[index][
            'settings']['index']['creation_date']
        if datetime.fromtimestamp(int(idx_creation_date) / 1000.0) < comparison_date:
            print "Index: " + index + " is older than " + age + " days"
            return index

    return None


def lambda_handler(event, context):
    '''Invoke Lambda '''
    # load config from json file in s3 bucket
    config = load_config(context)

    # create ES connection with sts auth file
    es_client = Elasticsearch(host=config['es_host'],
                              port=80,
                              connection_class=RequestsHttpConnection,
                              http_auth=sts_auth(config),
                              timeout=config['es_connection_timeout'])

    index_list = get_index_list(es_client)
    oldest_index = get_oldest_index(config, index_list)

    if oldest_index != None:
        print "Deleting Index: " + oldest_index
        delete_index(es_client, oldest_index)
    else:
        print "No old indexes found!"
