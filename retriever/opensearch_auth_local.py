import boto3
from requests_aws4auth import AWS4Auth

from retriever.opensearch import OpenSearchClient


def find_auth_opensearch(profile_name:str = 'sandbox'):

    session = boto3.Session(profile_name='sandbox')

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

    # Assume Created OpenSearch Admin Role
    session = boto3.Session(profile_name=profile_name)
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
    return {"host":host, "port":port, "auth":auth}


if __name__ == '__main__':
    config = find_auth_opensearch()
    client = OpenSearchClient(config, alias_name="jettro")

    print(client.ping())