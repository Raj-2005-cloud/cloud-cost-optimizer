from urllib import response

import boto3
from datetime import datetime, timedelta, UTC

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from accounts.models import AWSAccount, DismissedResource
from recommendations.utils import (
    analyze_ec2,
    analyze_ebs,
    analyze_s3,
    analyze_rds,
    send_email_alert,
)


@login_required
def scan_ec2(request):

    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

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

    try:
        response = ec2.describe_instances()
        reservations = response["Reservations"]
        is_mock = False
    except Exception:
        is_mock = True
        reservations = [
            {
                "Instances": [
                    {
                        "InstanceId": "i-0d5b4a92350ef912f",
                        "InstanceType": "t3.medium",
                        "State": {"Name": "running"},
                        "LaunchTime": datetime.now(UTC) - timedelta(days=12),
                        "Placement": {"AvailabilityZone": f"{aws.region}a"},
                        "Tags": [{"Key": "Name", "Value": "Production-API-Server"}],
                    },
                    {
                        "InstanceId": "i-09fca3783aefd0892",
                        "InstanceType": "m5.large",
                        "State": {"Name": "running"},
                        "LaunchTime": datetime.now(UTC) - timedelta(days=45),
                        "Placement": {"AvailabilityZone": f"{aws.region}b"},
                        "Tags": [{"Key": "Name", "Value": "Staging-Testing-Node"}],
                    },
                    {
                        "InstanceId": "i-012ab7d45129ef990",
                        "InstanceType": "t2.micro",
                        "State": {"Name": "stopped"},
                        "LaunchTime": datetime.now(UTC) - timedelta(days=90),
                        "Placement": {"AvailabilityZone": f"{aws.region}a"},
                        "Tags": [{"Key": "Name", "Value": "Legacy-Database-Backup"}],
                    }
                ]
            }
        ]

    instances = []

    for reservation in reservations:

        for instance in reservation["Instances"]:

            name = "N/A"

            if "Tags" in instance:
                for tag in instance["Tags"]:
                    if tag["Key"] == "Name":
                        name = tag["Value"]

            state = instance["State"]["Name"]

            cpu = 0

            if is_mock:
                if instance["InstanceId"] == "i-09fca3783aefd0892":
                    cpu = 1.8
                elif instance["InstanceId"] == "i-0d5b4a92350ef912f":
                    cpu = 45.0
            else:
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

            is_dismissed = DismissedResource.objects.filter(user=request.user, resource_id=instance["InstanceId"], service="EC2").exists()
            if is_dismissed:
                recommendation_text = "Approved / Confirmed OK"
                severity = "success"
                savings = 0
            else:
                recommendation_text = analysis["recommendation"]
                severity = analysis["severity"]
                savings = analysis["savings"]

            instances.append({
                "id": instance["InstanceId"],
                "name": name,
                "type": instance["InstanceType"],
                "state": state,
                "cpu": cpu,
                "public_ip": instance.get("PublicIpAddress", "-"),
                "launch_time": instance["LaunchTime"],
                "az": instance["Placement"]["AvailabilityZone"],

                "recommendation": recommendation_text,
                "severity": severity,
                "savings": savings,
                "is_dismissed": is_dismissed,
            })

    total_savings = sum(i["savings"] for i in instances)

    score = 100

    for i in instances:
        if i["severity"] == "warning":
            score -= 10

    if score < 0:
        score = 0

    running_count = sum(1 for i in instances if i["state"] == "running")

    return render(request, "scanner/ec2.html", {
        "instances": instances,
        "total_savings": total_savings,
        "score": score,
        "running_count": running_count,
        "is_mock": is_mock,
    })


@login_required
def scan_s3(request):

    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name=aws.region,
    )

    try:
        response = s3.list_buckets()
        bucket_list = response["Buckets"]
        is_mock = False
    except Exception:
        is_mock = True
        bucket_list = [
            {
                "Name": "company-billing-reports-2026",
                "CreationDate": datetime.now(UTC) - timedelta(days=200),
            },
            {
                "Name": "user-profile-thumbnails-staging",
                "CreationDate": datetime.now(UTC) - timedelta(days=50),
            },
            {
                "Name": "historical-logs-raw-archive",
                "CreationDate": datetime.now(UTC) - timedelta(days=400),
            }
        ]

    buckets = []

    for bucket in bucket_list:

        analysis = analyze_s3(bucket)

        file_count = 0
        try:
            objects_resp = s3.list_objects_v2(Bucket=bucket["Name"], MaxKeys=1000)
            if 'Contents' in objects_resp:
                file_count = len(objects_resp['Contents'])
                if objects_resp.get('IsTruncated'):
                    file_count = f"{file_count}+"
        except Exception:
            file_count = "unknown"

        is_dismissed = DismissedResource.objects.filter(user=request.user, resource_id=bucket["Name"], service="S3").exists()
        if is_dismissed:
            recommendation_text = "Approved / Confirmed OK"
            severity = "success"
            savings = 0
        else:
            recommendation_text = analysis["recommendation"]
            severity = analysis["severity"]
            savings = analysis["savings"]

        buckets.append({
            "name": bucket["Name"],
            "created": bucket["CreationDate"],
            "recommendation": recommendation_text,
            "severity": severity,
            "savings": savings,
            "file_count": file_count,
            "is_dismissed": is_dismissed,
        })

    return render(request, "scanner/s3.html", {
        "buckets": buckets,
        "is_mock": is_mock,
    })


@login_required
def scan_ebs(request):

    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name=aws.region,
    )

    try:
        response = ec2.describe_volumes()
        volume_list = response["Volumes"]
        is_mock = False
    except Exception:
        is_mock = True
        volume_list = [
            {
                "VolumeId": "vol-0a6eb9df23a5cfc02",
                "Size": 80,
                "VolumeType": "gp3",
                "State": "available",
                "AvailabilityZone": f"{aws.region}a",
                "Attachments": [],
            },
            {
                "VolumeId": "vol-0f37c2d119ae4b8a1",
                "Size": 250,
                "VolumeType": "io2",
                "State": "in-use",
                "AvailabilityZone": f"{aws.region}b",
                "Attachments": [{"InstanceId": "i-0d5b4a92350ef912f"}],
            }
        ]

    volumes = []

    for volume in volume_list:

        analysis = analyze_ebs({
            "attached": len(volume["Attachments"]) > 0,
        })

        is_dismissed = DismissedResource.objects.filter(user=request.user, resource_id=volume["VolumeId"], service="EBS").exists()
        if is_dismissed:
            recommendation_text = "Approved / Confirmed OK"
            severity = "success"
            savings = 0
        else:
            recommendation_text = analysis["recommendation"]
            severity = analysis["severity"]
            savings = analysis["savings"]

        volumes.append({
            "id": volume["VolumeId"],
            "size": volume["Size"],
            "type": volume["VolumeType"],
            "state": volume["State"],
            "az": volume["AvailabilityZone"],
            "attached": len(volume["Attachments"]) > 0,
            "recommendation": recommendation_text,
            "severity": severity,
            "savings": savings,
            "is_dismissed": is_dismissed,
        })

    return render(request, "scanner/ebs.html", {
        "volumes": volumes,
        "is_mock": is_mock,
    })
@login_required
def scan_rds(request):

    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    is_mock = False

    # Get all AWS regions
    try:
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=aws.access_key,
            aws_secret_access_key=aws.secret_key,
            region_name="ap-south-1",
        )
        regions = ec2.describe_regions()["Regions"]
    except Exception:
        is_mock = True
        regions = [{"RegionName": aws.region}]

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
            db_list = response["DBInstances"]
        except Exception:
            is_mock = True
            db_list = [
                {
                    "DBInstanceIdentifier": "prod-customer-db",
                    "Engine": "postgres",
                    "DBInstanceClass": "db.m5.large",
                    "DBInstanceStatus": "available",
                    "AllocatedStorage": 100,
                    "AvailabilityZone": f"{region_name}a",
                },
                {
                    "DBInstanceIdentifier": "dev-testing-replica",
                    "Engine": "mysql",
                    "DBInstanceClass": "db.t3.micro",
                    "DBInstanceStatus": "stopped",
                    "AllocatedStorage": 20,
                    "AvailabilityZone": f"{region_name}b",
                }
            ]

        try:
            for db in db_list:

                analysis = analyze_rds({
                    "status": db["DBInstanceStatus"],
                })

                is_dismissed = DismissedResource.objects.filter(user=request.user, resource_id=db["DBInstanceIdentifier"], service="RDS").exists()
                if is_dismissed:
                    recommendation_text = "Approved / Confirmed OK"
                    severity = "success"
                    savings = 0
                else:
                    recommendation_text = analysis["recommendation"]
                    severity = analysis["severity"]
                    savings = analysis["savings"]

                databases.append({
                    "identifier": db["DBInstanceIdentifier"],
                    "engine": db["Engine"],
                    "class": db["DBInstanceClass"],
                    "status": db["DBInstanceStatus"],
                    "storage": db["AllocatedStorage"],
                    "az": db["AvailabilityZone"],
                    "region": region_name,
                    "recommendation": recommendation_text,
                    "severity": severity,
                    "savings": savings,
                    "is_dismissed": is_dismissed,
                })
        except Exception as e:
                   print(f"Region: {region_name}")
                   print("ERROR:", e)

    return render(
        request,
        "scanner/rds.html",
        {
            "databases": databases,
            "is_mock": is_mock,
        },
    )


@login_required
def stop_ec2_instance(request, instance_id):
    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    if request.method == "POST":
        try:
            ec2 = boto3.client(
                "ec2",
                aws_access_key_id=aws.access_key,
                aws_secret_access_key=aws.secret_key,
                region_name=aws.region,
            )
            ec2.stop_instances(InstanceIds=[instance_id])
            from django.contrib import messages
            messages.success(request, f"Successfully stopped EC2 instance {instance_id}.")
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Failed to stop instance: {str(e)}")

    return redirect("scan_ec2")


@login_required
def terminate_ec2_instance(request, instance_id):
    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    if request.method == "POST":
        try:
            ec2 = boto3.client(
                "ec2",
                aws_access_key_id=aws.access_key,
                aws_secret_access_key=aws.secret_key,
                region_name=aws.region,
            )
            ec2.terminate_instances(InstanceIds=[instance_id])
            from django.contrib import messages
            messages.success(request, f"Successfully terminated EC2 instance {instance_id}.")
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Failed to terminate instance: {str(e)}")

    return redirect("scan_ec2")


@login_required
def delete_ebs_volume(request, volume_id):
    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    if request.method == "POST":
        try:
            ec2 = boto3.client(
                "ec2",
                aws_access_key_id=aws.access_key,
                aws_secret_access_key=aws.secret_key,
                region_name=aws.region,
            )
            ec2.delete_volume(VolumeId=volume_id)
            from django.contrib import messages
            messages.success(request, f"Successfully deleted EBS volume {volume_id}.")
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Failed to delete volume: {str(e)}")

    return redirect("scan_ebs")


@login_required
def delete_rds_instance(request, region_name, db_id):
    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    if request.method == "POST":
        try:
            rds = boto3.client(
                "rds",
                aws_access_key_id=aws.access_key,
                aws_secret_access_key=aws.secret_key,
                region_name=region_name,
            )
            rds.delete_db_instance(
                DBInstanceIdentifier=db_id,
                SkipFinalSnapshot=True
            )
            from django.contrib import messages
            messages.success(request, f"Successfully requested deletion of RDS instance {db_id} in region {region_name}.")
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Failed to delete RDS instance: {str(e)}")

    return redirect("scan_rds")


@login_required
def delete_s3_bucket(request, bucket_name):
    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    if request.method == "POST":
        try:
            s3 = boto3.client(
                "s3",
                aws_access_key_id=aws.access_key,
                aws_secret_access_key=aws.secret_key,
                region_name=aws.region,
            )
            # Empty bucket first
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    objects = [{'Key': obj['Key']} for obj in page['Contents']]
                    s3.delete_objects(Bucket=bucket_name, Delete={'Objects': objects})
            # Delete bucket
            s3.delete_bucket(Bucket=bucket_name)
            from django.contrib import messages
            messages.success(request, f"Successfully emptied and deleted S3 bucket {bucket_name}.")
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Failed to delete S3 bucket: {str(e)}")

    return redirect("scan_s3")


@login_required
def dismiss_resource(request, service, resource_id):
    if request.method == "POST":
        DismissedResource.objects.get_or_create(
            user=request.user,
            resource_id=resource_id,
            defaults={"service": service.upper()}
        )
        from django.contrib import messages
        messages.success(request, f"Cost recommendation for {service} resource {resource_id} has been approved and marked as OK.")

        # Send cost alert snoozed confirmation email
        aws = AWSAccount.objects.filter(user=request.user).first()
        if aws and aws.alert_email:
            send_email_alert(
                aws.alert_email,
                "Cost Alert Snoozed",
                f"Optimizer Alert: Cost recommendation for {service} resource '{resource_id}' was confirmed OK. Alerts for this resource are stopped."
            )

    referer = request.META.get('HTTP_REFERER', '')
    if 'alerts' in referer:
        return redirect("alert_center")

    redirect_map = {
        "EC2": "scan_ec2",
        "EBS": "scan_ebs",
        "S3": "scan_s3",
        "RDS": "scan_rds",
    }
    return redirect(redirect_map.get(service.upper(), "dashboard"))


@login_required
def alert_center(request):
    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    alerts = []
    access_key = aws.access_key
    secret_key = aws.secret_key
    region = aws.region
    alert_email = aws.alert_email

    # 1. EC2
    try:
        ec2 = boto3.client("ec2", aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
        reservations = ec2.describe_instances()["Reservations"]
        for r in reservations:
            for instance in r["Instances"]:
                is_dismissed = DismissedResource.objects.filter(user=request.user, resource_id=instance["InstanceId"], service="EC2").exists()
                if not is_dismissed:
                    analysis = analyze_ec2({"state": instance["State"]["Name"], "cpu": 0})
                    if analysis["savings"] > 0:
                        alerts.append({
                            "service": "EC2",
                            "resource_id": instance["InstanceId"],
                            "message": f"EC2 instance {instance['InstanceId']} is in state '{instance['State']['Name']}'. Consider stopping or terminating it.",
                            "savings": analysis["savings"],
                            "channel": f"Email ({alert_email})" if alert_email else "Slack (#billing-alerts)",
                        })
    except Exception:
        pass

    # 2. EBS
    try:
        ec2 = boto3.client("ec2", aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
        volumes = ec2.describe_volumes()["Volumes"]
        for vol in volumes:
            is_dismissed = DismissedResource.objects.filter(user=request.user, resource_id=vol["VolumeId"], service="EBS").exists()
            if not is_dismissed:
                analysis = analyze_ebs({"attached": len(vol["Attachments"]) > 0})
                if analysis["savings"] > 0:
                    alerts.append({
                        "service": "EBS",
                        "resource_id": vol["VolumeId"],
                        "message": f"EBS Volume {vol['VolumeId']} (Size: {vol['Size']} GB) is unattached. Consider deleting it to save costs.",
                        "savings": analysis["savings"],
                        "channel": f"Email ({alert_email})" if alert_email else "Email (devops@company.com)",
                    })
    except Exception:
        pass

    # 3. RDS
    try:
        rds = boto3.client("rds", aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
        databases = rds.describe_db_instances()["DBInstances"]
        for db in databases:
            is_dismissed = DismissedResource.objects.filter(user=request.user, resource_id=db["DBInstanceIdentifier"], service="RDS").exists()
            if not is_dismissed:
                analysis = analyze_rds({"status": db["DBInstanceStatus"]})
                if analysis["savings"] > 0:
                    alerts.append({
                        "service": "RDS",
                        "resource_id": db["DBInstanceIdentifier"],
                        "message": f"RDS Instance {db['DBInstanceIdentifier']} is in status '{db['DBInstanceStatus']}'. Review its sizing and status.",
                        "savings": analysis["savings"],
                        "channel": f"Email ({alert_email})" if alert_email else "Slack (#rds-alerts)",
                    })
    except Exception:
        pass

    # 4. S3
    try:
        s3 = boto3.client("s3", aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
        buckets = s3.list_buckets()["Buckets"]
        for bucket in buckets:
            is_dismissed = DismissedResource.objects.filter(user=request.user, resource_id=bucket["Name"], service="S3").exists()
            if not is_dismissed:
                analysis = analyze_s3(bucket)
                if analysis["savings"] > 0:
                    alerts.append({
                        "service": "S3",
                        "resource_id": bucket["Name"],
                        "message": f"S3 Bucket '{bucket['Name']}' does not have Intelligent-Tiering enabled. Cost can be optimized.",
                        "savings": analysis["savings"],
                        "channel": f"Email ({alert_email})" if alert_email else "Email (billing@company.com)",
                    })
    except Exception:
        pass

    return render(request, "scanner/alerts.html", {
        "alerts": alerts,
    })