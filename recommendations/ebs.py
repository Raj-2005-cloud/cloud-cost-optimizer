def analyze_ebs(volume):

    if not volume["attached"]:
        return {
            "recommendation": "Delete unattached volume",
            "severity": "warning",
            "savings": 8,
        }

    return {
        "recommendation": "Volume is healthy",
        "severity": "success",
        "savings": 0,
    }