from urllib import response

import boto3
from datetime import datetime, timedelta, UTC

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from accounts.models import AWSAccount
from recommendations.utils import analyze_ec2


@login_required
def scan_ec2(request):

    aws = AWSAccount.objects.get(user=request.user)

    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name=aws.region,
    )

    cloudwatch = boto3.client(
        "cloudwatch",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name=aws.region,
    )

    response = ec2.describe_instances()

    instances = []

    for reservation in response["Reservations"]:

        for instance in reservation["Instances"]:

            name = "N/A"

            if "Tags" in instance:
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name":
                        name = tag["Value"]

            state = instance["State"]["Name"]

            cpu = 0

            try:

                metrics = cloudwatch.get_metric_statistics(
                    Namespace="AWS/EC2",
                    MetricName="CPUUtilization",
                    Dimensions=[
                        {
                            "Name": "InstanceId",
                            "Value": instance["InstanceId"],
                        }
                    ],
                    StartTime=datetime.now(UTC) - timedelta(days=7),
                    EndTime=datetime.now(UTC),
                    Period=86400,
                    Statistics=["Average"],
                )

                datapoints = metrics["Datapoints"]

                if datapoints:
                    cpu = round(
                        sum(point["Average"] for point in datapoints)
                        / len(datapoints),
                        2,
                    )

            except Exception:
                cpu = 0

            analysis = analyze_ec2({
                "state": state,
                "cpu": cpu,
            })

            instances.append({
                "id": instance["InstanceId"],
                "name": name,
                "type": instance["InstanceType"],
                "state": state,
                "cpu": cpu,
                "public_ip": instance.get("PublicIpAddress", "-"),
                "launch_time": instance["LaunchTime"],
                "az": instance["Placement"]["AvailabilityZone"],

                "recommendation": analysis["recommendation"],
                "severity": analysis["severity"],
                "savings": analysis["savings"],
            })

    total_savings = sum(i["savings"] for i in instances)

    score = 100

    for i in instances:
        if i["severity"] == "warning":
            score -= 10

    if score < 0:
        score = 0

    return render(request, "scanner/ec2.html", {
        "instances": instances,
        "total_savings": total_savings,
        "score": score,
    })


@login_required
def scan_s3(request):

    aws = AWSAccount.objects.get(user=request.user)

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name=aws.region,
    )

    response = s3.list_buckets()

    buckets = []

    for bucket in response["Buckets"]:

        buckets.append({
            "name": bucket["Name"],
            "created": bucket["CreationDate"],
        })

    return render(request, "scanner/s3.html", {
        "buckets": buckets,
    })


@login_required
def scan_ebs(request):

    aws = AWSAccount.objects.get(user=request.user)

    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name=aws.region,
    )

    response = ec2.describe_volumes()

    volumes = []

    for volume in response["Volumes"]:

        volumes.append({
            "id": volume["VolumeId"],
            "size": volume["Size"],
            "type": volume["VolumeType"],
            "state": volume["State"],
            "az": volume["AvailabilityZone"],
            "attached": len(volume["Attachments"]) > 0,
        })

    return render(request, "scanner/ebs.html", {
        "volumes": volumes,
    })
@login_required
def scan_rds(request):

    aws = AWSAccount.objects.get(user=request.user)

    # Get all AWS regions
    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name="ap-south-1",
    )

    regions = ec2.describe_regions()["Regions"]

    databases = []

    for region in regions:

        region_name = region["RegionName"]

        rds = boto3.client(
            "rds",
            aws_access_key_id=aws.access_key,
            aws_secret_access_key=aws.secret_key,
            region_name=region_name,
        )

        try:

            response = rds.describe_db_instances()
            print("Region:", region_name)
            print(response)

            for db in response["DBInstances"]:

                recommendation = "Healthy"
                savings = 0
                severity = "success"

                if db["DBInstanceStatus"] != "available":
                    recommendation = "Review database status."
                    severity = "warning"

                databases.append({
                    "identifier": db["DBInstanceIdentifier"],
                    "engine": db["Engine"],
                    "class": db["DBInstanceClass"],
                    "status": db["DBInstanceStatus"],
                    "storage": db["AllocatedStorage"],
                    "az": db["AvailabilityZone"],
                    "region": region_name,
                    "recommendation": recommendation,
                    "severity": severity,
                    "savings": savings,
                })

        except Exception as e:
                  print(f"Region: {region_name}")
                  print("ERROR:", e)

    return render(
        request,
        "scanner/rds.html",
        {
            "databases": databases,
        },
    )