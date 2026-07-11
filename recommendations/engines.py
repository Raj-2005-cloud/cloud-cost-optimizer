def generate_recommendations(ec2_instances, ebs_volumes, s3_buckets, rds_instances):

    recommendations = []

    # EC2
    for instance in ec2_instances:

        if instance["state"] == "stopped":
            recommendations.append({
                "severity": "High",
                "service": "EC2",
                "title": f"Terminate {instance['name']}",
                "saving": 300,
            })

        elif instance.get("cpu", 100) < 5:
            recommendations.append({
                "severity": "Medium",
                "service": "EC2",
                "title": f"Downsize {instance['name']}",
                "saving": 120,
            })

    # EBS
    for volume in ebs_volumes:

        if not volume["attached"]:
            recommendations.append({
                "severity": "High",
                "service": "EBS",
                "title": f"Delete {volume['id']}",
                "saving": 90,
            })

    # S3
    for bucket in s3_buckets:

        recommendations.append({
            "severity": "Low",
            "service": "S3",
            "title": f"Enable Intelligent Tiering ({bucket['name']})",
            "saving": 25,
        })

    # RDS
    for db in rds_instances:

        if db["status"] != "available":
            recommendations.append({
                "severity": "Medium",
                "service": "RDS",
                "title": f"Review {db['identifier']}",
                "saving": 150,
            })

    return recommendations