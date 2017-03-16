# Lambda Elasticsearch Index Cleaner
Lambda function to cleanup index's according to age

## Prerequisites
* Admin Acess to: AWS S3, Elasticsearch, Lambda, IAM
* aws cli
* python 2.7+
* boto3
* virtualenv
* jq

## Setup
### IAM
* create the lambda IAM role
```
aws iam create-role --role-name lambda-elasticsearch-index-cleaner --assume-role-policy-document="$(cat aws_role_policies/trust-policy.json|jq -c '.' )"
```
* modify the role so that it can assume itself for STS token generation
```
aws iam update-assume-role-policy --policy-document="$(cat aws_role_policies/trust-policy-mod.json|jq -c '.')" --role-name lambda-elasticsearch-index-cleaner
```
* Add access policies to allow 
 * S3 readonly 
 * ES access
 * Basic Lambda execution (aka cloudwatch logs) 

### S3
* create the bucket where the lambda function config will be stored
```
aws s3 mb s3://lambda-elasticsearch-index-cleaner-config --region eu-west-1
```
* create the bucket where lambda function deployment zip will be stored
```
aws s3 mb s3://lambda-elasticsearch-index-cleaner --region eu-west-1
```
* Create 4 folders to hold config files for different deployment stages thorugh the AWS S3 console:
```
$LATEST
DEV
STAGE
PROD
```
### Elasticsearch
Permissions policy should allow calls from the lamda role, however in my case I have this open to the domain.
You will need to get your ES endpoint URL


* install needed python dep's
```
pip install virtualenv boto3
```
* clone the repo
```
 git clone https://github.com/dbnegative/lambda-elasticsearch-index-cleaner
 cd lambda-elasticsearch-index-cleaner
```
* edit the config/deployment-config.json if needed. 
```
{
"S3_CONFIG_BUCKET":"lambda-elasticsearch-index-cleaner",
"LAMBDA_DEPLOY_BUCKET": "lambda-elasticsearch-index-cleaner",
"CONFIG_FILE":"config.json",
"LAMBDA_FUNC_NAME" :"lambda-elasticsearch-index-cleaner",
"LAMBDA_HANDLER":"lambda_function.lambda_function",
"LAMBDA_ROLE_ARN":"arn:aws:iam::<YOURAWSACCOUNTID>:role/lambda-elasticsearch-index-cleaner",
"LAMBDA_TIMEOUT":"120",
"LAMBDA_MEMORY_SIZE":"128"
}
```
* setup the build enviroment
```
deploy-wrapper.py setup
```
* edit the config/config.json with your own settings, at the minimum the following:
 * set expiry age in days, logs older than this will be deleted
 * string-match should be the log index prefix that will be deleted. i.e a string match of "cloudfrontlog" would match indexes called cloudfrontlog-2016-10-21
```
{
    "es_host": "search-cloudfront-logging-sfgveenrrv6a2d52t5svjyvnzy.eu-west-1.es.amazonaws.com",
    "es_region": "eu-west-1",
    "es_connection_timeout": 60,
    "sts_role_arn": "arn:aws:iam::688390856993:role/lambda-elasticsearch-index-clean",
    "sts_session_name": "lambda-elasticsearch-index-clean",
    "string-match": "cloudfrontlog",
    "expiry-age": "4"
}
```
* create the initial version of the function using the deploy-wrapper.sh
```
deploy-wrapper.py init
```
* create 3 lambda alias for continous deploments and tests 
```
aws lambda create-alias --name DEV --function-name lambda-elasticsearch-index-cleaner --function-version=1
aws lambda create-alias --name STAGE --function-name lambda-elasticsearch-index-cleaner --function-version=1
aws lambda create-alias --name PROD --function-name lambda-elasticsearch-index-cleanerr --function-version=1
```
* create s3 trigger on PROD alias. You can now deploy and test to DEV and STAGE without affecting your production version
  1. go to the lambda console
  2. select the lambda-elasticsearch-index-cleaner fucntion
  3. press the "Qualifiers" button and select the PROD alias
  4. select the "Triggers" tab
  5. add an Cloudwatch Scheduled event trigger
  6. name the rule to something appropriate
  7. set the event to trigger every day
  8. enable the trigger and save

* deploying a new build to DEV alias
```
deploy-wrapper.py deploy --env DEV
```
* promoting that version to STAGE alias
```
deploy-wrapper.py promote DEV STAGE
```

# Deploy-wrapper.py usage
```
Deploy and manipulate lambda function

positional arguments:
  {promote,deploy,config,clean,setup}
                        [CMDS...]
    promote             promote <source enviroment> version to <target
                        enviroment>
    deploy              deploy function to s3
    config              deploy config to s3
    init                creates the base lambda function
    clean               clean local build enviroment
    setup               create local build enviroment

optional arguments:
  -h, --help            show this help message and exit
```

## TODO
* aws policy files - S3, ELASTICSEARCH, LOG 
* improve instructions aka this file
