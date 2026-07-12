from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from accounts.models import AWSAccount
from recommendations.utils import (
    analyze_ec2,
    analyze_ebs,
    analyze_s3,
    analyze_rds,
)

import boto3
from datetime import datetime, timedelta


def home(request):
    return render(request, "home.html")


@login_required
def dashboard(request):
    aws_account = AWSAccount.objects.filter(user=request.user).first()

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "aws_account": aws_account,
        },
    )


@login_required
def analytics(request):

    aws = AWSAccount.objects.filter(user=request.user).first()

    if not aws:
        return redirect("connect_aws")

    access_key = aws.access_key
    secret_key = aws.secret_key
    region = aws.region

    # ==========================
    # EC2
    # ==========================

    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    try:
        reservations = ec2.describe_instances()["Reservations"]
    except Exception:
        reservations = []

    ec2_count = sum(len(r["Instances"]) for r in reservations)

    # ==========================
    # S3
    # ==========================

    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    try:
        buckets = s3.list_buckets()["Buckets"]
    except Exception:
        buckets = []

    bucket_count = len(buckets)

    # ==========================
    # EBS
    # ==========================

    try:
        volumes = ec2.describe_volumes()["Volumes"]
    except Exception:
        volumes = []

    ebs_count = len(volumes)

    # ==========================
    # RDS
    # ==========================

    rds = boto3.client(
        "rds",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    try:
        databases = rds.describe_db_instances()["DBInstances"]
    except Exception:
        databases = []

    rds_count = len(databases)

    # ==========================
    # TOTAL RESOURCES
    # ==========================

    total_resources = (
        ec2_count +
        bucket_count +
        ebs_count +
        rds_count
    )

    # ==========================
    # BILLING
    # ==========================

    ce = boto3.client(
        "ce",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )

    end = datetime.utcnow().date()
    start = end - timedelta(days=30)

    pie_labels = []
    pie_values = []
    total_cost = 0

    try:
        response = ce.get_cost_and_usage(
            TimePeriod={
                "Start": str(start),
                "End": str(end),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SERVICE",
                }
            ],
        )

        for group in response["ResultsByTime"][0]["Groups"]:

            service = group["Keys"][0]
            cost = round(
                float(group["Metrics"]["UnblendedCost"]["Amount"]),
                2,
            )

            pie_labels.append(service)
            pie_values.append(cost)

            total_cost += cost
    except Exception:
        pass

    # ==========================
    # DASHBOARD METRICS
    # ==========================

    recommendations = []
    savings = 0

    # ==========================
    # EC2 Recommendations
    # ==========================

    for reservation in reservations:
        for instance in reservation["Instances"]:

            analysis = analyze_ec2({
                "state": instance["State"]["Name"],
                "cpu": 0,
            })

            if analysis["savings"] > 0:
                recommendations.append({
                    "service": "EC2",
                    "text": analysis["recommendation"],
                    "savings": analysis["savings"],
                })
                savings += analysis["savings"]

    # ==========================
    # EBS Recommendations
    # ==========================

    for volume in volumes:

        analysis = analyze_ebs({
            "attached": len(volume["Attachments"]) > 0,
        })

        if analysis["savings"] > 0:
            recommendations.append({
                "service": "EBS",
                "text": analysis["recommendation"],
                "savings": analysis["savings"],
            })
            savings += analysis["savings"]

    # ==========================
    # S3 Recommendations
    # ==========================

    for bucket in buckets:

        analysis = analyze_s3(bucket)

        if analysis["savings"] > 0:
            recommendations.append({
                "service": "S3",
                "text": analysis["recommendation"],
                "savings": analysis["savings"],
            })
            savings += analysis["savings"]

    # ==========================
    # RDS Recommendations
    # ==========================

    for db in databases:

        analysis = analyze_rds({
            "status": db["DBInstanceStatus"],
        })

        if analysis["savings"] > 0:
            recommendations.append({
                "service": "RDS",
                "text": analysis["recommendation"],
                "savings": analysis["savings"],
            })
            savings += analysis["savings"]

    # ==========================
    # Optimization Score
    # ==========================

    score = max(100 - len(recommendations) * 10, 0)

    trend = [
        total_cost,
        total_cost,
        total_cost,
        total_cost,
    ]

    return render(
        request,
        "dashboard/analytics.html",
        {
            "total_cost": round(total_cost, 2),
            "total_resources": total_resources,
            "savings": savings,
            "score": score,
            "pie_labels": pie_labels,
            "pie_values": pie_values,
            "trend": trend,
            "recommendations": recommendations,
        },
    )