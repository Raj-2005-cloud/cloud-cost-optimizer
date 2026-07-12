import boto3

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from accounts.models import AWSAccount
from optimizer.utils import (
    analyze_ec2,
    analyze_ebs,
    analyze_rds,
    analyze_s3,
)


@login_required
def recommendations(request):

    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    recommendations = []

    # ---------------- EC2 ----------------

    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name=aws.region,
    )

    response = ec2.describe_instances()

    for reservation in response["Reservations"]:

        for instance in reservation["Instances"]:

            state = instance["State"]["Name"]

            analysis = analyze_ec2({
                "state": state,
                "cpu": 0,
            })

            recommendations.append({
                "service": "EC2",
                "resource": instance["InstanceId"],
                "recommendation": analysis["recommendation"],
                "savings": analysis["savings"],
                "severity": analysis["severity"],
            })

    # ---------------- EBS ----------------

    volumes = ec2.describe_volumes()

    for volume in volumes["Volumes"]:

        analysis = analyze_ebs({
            "attached": len(volume["Attachments"]) > 0,
        })

        recommendations.append({
            "service": "EBS",
            "resource": volume["VolumeId"],
            "recommendation": analysis["recommendation"],
            "savings": analysis["savings"],
            "severity": analysis["severity"],
        })

    # ---------------- RDS ----------------

    rds = boto3.client(
        "rds",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name=aws.region,
    )

    response = rds.describe_db_instances()

    for db in response["DBInstances"]:

        analysis = analyze_rds({
            "status": db["DBInstanceStatus"],
        })

        recommendations.append({
            "service": "RDS",
            "resource": db["DBInstanceIdentifier"],
            "recommendation": analysis["recommendation"],
            "savings": analysis["savings"],
            "severity": analysis["severity"],
        })

    # ---------------- S3 ----------------

    s3 = boto3.client(
        "s3",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
    )

    response = s3.list_buckets()

    for bucket in response["Buckets"]:

        analysis = analyze_s3(bucket)

        recommendations.append({
            "service": "S3",
            "resource": bucket["Name"],
            "recommendation": analysis["recommendation"],
            "savings": analysis["savings"],
            "severity": analysis["severity"],
        })

    total = sum(r["savings"] for r in recommendations)

    return render(
        request,
        "optimizer/dashboard.html",
        {
            "recommendations": recommendations,
            "total": total,
        },
    )