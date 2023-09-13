import os

import boto3
from opensearchpy import AWSV4SignerAuth
from requests_aws4auth import AWS4Auth

from retriever.opensearch import OpenSearchClient


def find_auth_opensearch(profile_name: str = 'sandbox'):
    is_local = 'AWS_SAGEMAKER_PYTHONNOUSERSITE' not in os.environ
    if is_local:
        session = boto3.Session(profile_name=profile_name)
    else:
        session = boto3.Session()

    # Fetch outputs of the CloudFormation stack
    cfn = session.client('cloudformation')
    response = cfn.describe_stacks(
        StackName='OSSGStack-OpenSearchNestedStackOpenSearchNestedStackResource203C0F43-58JJBAIMFZI5'
    )

    outputs = {
        output['ExportName']: output['OutputValue']
        for output in response['Stacks'][0]['Outputs']
        if 'ExportName' in output
    }

    # Extract the OpenSearch endpoint
    host = outputs['cdk-os-sg-DomainEndpoint']
    port = 443
    region = 'eu-west-1'  # e.g. us-west-1

    if is_local:
        # Assume Created OpenSearch Admin Role
        sts = session.client('sts')
        response = sts.assume_role(
            RoleArn=outputs['cdk-os-sg-AdminUserRoleArn'],
            RoleSessionName="assumed-opensearch-user-admin-role",
        )

        # Create OpenSearch client
        auth = AWS4Auth(
            response['Credentials']['AccessKeyId'], response['Credentials']['SecretAccessKey'],
            region, 'es',
            session_token=response['Credentials']['SessionToken']
        )
    else:
        credentials = session.get_credentials()
        auth = AWSV4SignerAuth(credentials, region)

    return {"host": host, "port": port, "auth": auth}


if __name__ == '__main__':
    client = OpenSearchClient(find_auth_opensearch())

    print(client.ping())
