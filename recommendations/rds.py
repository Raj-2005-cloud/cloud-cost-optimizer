def analyze_rds(db):

    if db["status"] != "available":
        return {
            "recommendation": "Review database status",
            "severity": "warning",
            "savings": 0,
        }

    return {
        "recommendation": "Database is healthy",
        "severity": "success",
        "savings": 0,
    }