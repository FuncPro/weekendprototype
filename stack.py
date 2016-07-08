#!/usr/bin/env python

import sys

from troposphere import Template, Ref, Output, Parameter, Join, GetAtt
from troposphere.route53 import RecordSetType, RecordSet, RecordSetGroup, AliasTarget
from troposphere.s3 import Bucket, PublicRead, BucketOwnerFullControl, WebsiteConfiguration, RedirectAllRequestsTo

import boto3
import botocore


t = Template()


hostedzone = t.add_parameter(Parameter(
    "HostedZone",
    Description="The DNS name of an existing Amazon Route 53 hosted zone",
    Type="String",
))


root_bucket = t.add_resource(
    Bucket("RootBucket",
           AccessControl=PublicRead,
           WebsiteConfiguration=WebsiteConfiguration(
               IndexDocument="index.html",
           )
    ))
www_bucket = t.add_resource(Bucket("WWWBucket", AccessControl=BucketOwnerFullControl, WebsiteConfiguration=WebsiteConfiguration(
    RedirectAllRequestsTo=RedirectAllRequestsTo(
        HostName=Ref(root_bucket)
    )
)))


record = t.add_resource(RecordSetGroup(
    'RecordSetGroup',
    HostedZoneName=Join("", [Ref(hostedzone), "."]),
    RecordSets=[
        RecordSet(
            Name=Ref(hostedzone),
            Type='A',
            AliasTarget=AliasTarget(
                hostedzoneid='Z1BKCTXD74EZPE',
                dnsname='s3-website-eu-west-1.amazonaws.com',
            )
        ),
        RecordSet(
            Name=Join('.', ['www', Ref(hostedzone)]),
            Type='CNAME',
            TTL='900',
            ResourceRecords=[
                GetAtt(www_bucket, 'DomainName')
            ]
        ),
    ]
))


t.add_output(Output(
    "BucketName",
    Value=Ref(root_bucket),
    Description="Name of S3 bucket to hold website content"
))


#print(t.to_json())
#print(t.outputs['BucketName'].Value.data)

domain = sys.argv[1]
stack_name = domain.replace('.', '')

client = boto3.client('cloudformation', region_name='eu-west-1')
try:
    response = client.describe_stacks(
        StackName=stack_name,
    )
except botocore.exceptions.ClientError:
    client.create_stack(
        StackName=stack_name,
        TemplateBody=t.to_json(),
        Parameters=[
            {'ParameterKey': 'HostedZone', 'ParameterValue': domain},
         ],
    )
    waiter = client.get_waiter('stack_create_complete')
    waiter.wait(StackName=stack_name)
    response = client.describe_stacks(
        StackName=stack_name,
    )

    
print(response['Stacks'][0]['Outputs'][0]['OutputValue'])
