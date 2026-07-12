import boto3
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas

from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from accounts.models import AWSAccount
from recommendations.utils import (
    analyze_ec2,
    analyze_ebs,
    analyze_s3,
    analyze_rds,
)


@login_required
def generate_pdf(request):
    # Ensure AWS Account is connected
    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    access_key = aws.access_key
    secret_key = aws.secret_key
    region = aws.region

    # Initialize boto3 clients
    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    rds = boto3.client(
        "rds",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    ce = boto3.client(
        "ce",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )

    # 1. EC2 Scanning
    ec2_count = 0
    recommendations = []
    total_savings = 0

    try:
        reservations = ec2.describe_instances()["Reservations"]
        for r in reservations:
            for instance in r["Instances"]:
                ec2_count += 1
                analysis = analyze_ec2({
                    "state": instance["State"]["Name"],
                    "cpu": 0,
                })
                if analysis["savings"] > 0:
                    recommendations.append(
                        ("EC2", f"{analysis['recommendation']} ({instance['InstanceId']})", analysis["savings"])
                    )
                    total_savings += analysis["savings"]
    except Exception:
        pass

    # 2. EBS Scanning
    ebs_count = 0
    try:
        volumes = ec2.describe_volumes()["Volumes"]
        ebs_count = len(volumes)
        for volume in volumes:
            analysis = analyze_ebs({
                "attached": len(volume["Attachments"]) > 0,
            })
            if analysis["savings"] > 0:
                recommendations.append(
                    ("EBS", f"{analysis['recommendation']} ({volume['VolumeId']})", analysis["savings"])
                )
                total_savings += analysis["savings"]
    except Exception:
        pass

    # 3. S3 Scanning
    s3_count = 0
    try:
        buckets = s3.list_buckets()["Buckets"]
        s3_count = len(buckets)
        for bucket in buckets:
            analysis = analyze_s3(bucket)
            if analysis["savings"] > 0:
                recommendations.append(
                    ("S3", f"{analysis['recommendation']} ({bucket['Name']})", analysis["savings"])
                )
                total_savings += analysis["savings"]
    except Exception:
        pass

    # 4. RDS Scanning
    rds_count = 0
    try:
        databases = rds.describe_db_instances()["DBInstances"]
        rds_count = len(databases)
        for db in databases:
            analysis = analyze_rds({
                "status": db["DBInstanceStatus"],
            })
            if analysis["savings"] > 0:
                recommendations.append(
                    ("RDS", f"{analysis['recommendation']} ({db['DBInstanceIdentifier']})", analysis["savings"])
                )
                total_savings += analysis["savings"]
    except Exception:
        pass

    # 5. Billing Analysis
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)
    current_cost = 0

    try:
        response = ce.get_cost_and_usage(
            TimePeriod={
                "Start": str(start_date),
                "End": str(end_date),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
        )
        current_cost = round(
            float(response["ResultsByTime"][0]["Total"]["UnblendedCost"]["Amount"]),
            2,
        )
    except Exception:
        pass

    # Write PDF response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="Cloud_Cost_Report.pdf"'

    p = canvas.Canvas(response)

    # Title
    p.setFont("Helvetica-Bold", 18)
    p.drawString(180, 800, "Cloud Cost Optimizer Report")

    # Metadata
    p.setFont("Helvetica", 10)
    p.drawString(50, 760, f"Generated On: {datetime.now().strftime('%d-%m-%Y %H:%M')}")
    p.drawString(50, 745, f"Region: {region}")

    # Summary
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, 710, "Executive Summary")

    p.setFont("Helvetica", 11)
    p.drawString(70, 685, f"• Scanned {ec2_count} EC2 instances, {s3_count} S3 buckets, {ebs_count} EBS volumes, and {rds_count} RDS databases.")
    p.drawString(70, 665, f"• Current month cost (estimated): ${current_cost}")
    p.drawString(70, 645, f"• Total potential savings identified: ${total_savings}/month")

    # Recommendations Section
    y = 600
    p.setFont("Helvetica-Bold", 14)
    p.drawString(50, y, "Cost Optimization Recommendations")
    y -= 25

    p.setFont("Helvetica", 11)
    if recommendations:
        for service, desc, savings in recommendations[:10]: # Cap at 10 items to prevent overflow
            p.drawString(70, y, f"• [{service}] {desc} - Save: ${savings}/month")
            y -= 20
            if y < 100:  # Page boundary simple check
                p.showPage()
                y = 750
                p.setFont("Helvetica", 11)
    else:
        p.drawString(70, y, "No wasted resources or optimization recommendations found. Infrastructure is healthy!")
        y -= 20

    # Footer
    if y > 100:
        y = 100
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(50, y, "This report was generated dynamically by the Cloud Cost Optimizer application.")

    p.showPage()
    p.save()

    return response