#!/usr/bin/env python3
"""
Analyze IAMSentry IAM recommendations and create actionable CSV reports
"""

import csv
import json
import os
from collections import defaultdict


def analyze_iam_recommendations(json_file):
    """Analyze the IAM recommendations JSON file and extract key insights."""

    print(f"Analyzing {json_file}...")

    # Load the JSON data
    with open(json_file, "r") as f:
        recommendations = json.load(f)

    print(f"Found {len(recommendations)} recommendations")

    # Data structures to collect information
    user_actions = []
    role_usage_analysis = defaultdict(
        lambda: {
            "users": set(),
            "total_permissions": 0,
            "used_permissions": 0,
            "recommendations": [],
        }
    )

    # Process each recommendation
    for rec in recommendations:
        processor = rec.get("processor", {})
        raw = rec.get("raw", {})
        score = rec.get("score", {})

        # Extract key information
        account_id = processor.get("account_id", "N/A")
        account_type = processor.get("account_type", "N/A")
        project = processor.get("project", "N/A")

        # Get role and action information from raw data
        content = raw.get("content", {})
        overview = content.get("overview", {})

        member = overview.get("member", account_id)
        removed_role = overview.get("removedRole", "N/A")
        description = raw.get("description", "N/A")

        # Get permissions info from insights
        insights = raw.get("insights", [])
        total_perms = 0
        used_perms = 0
        exercised_perms = []

        if insights:
            insight_content = insights[0].get("content", {})
            total_perms = int(insight_content.get("currentTotalPermissionsCount", 0))
            raw_exercised = insight_content.get("exercisedPermissions", [])
            # Handle case where permissions might be objects instead of strings
            exercised_perms = []
            for perm in raw_exercised:
                if isinstance(perm, str):
                    exercised_perms.append(perm)
                elif isinstance(perm, dict):
                    # If it's a dict, try to extract permission name
                    exercised_perms.append(perm.get("permission", str(perm)))
                else:
                    exercised_perms.append(str(perm))
            used_perms = len(exercised_perms)

        # Calculate waste percentage
        waste_percentage = 0
        if total_perms > 0:
            waste_percentage = ((total_perms - used_perms) / total_perms) * 100

        # Risk score
        risk_score = score.get("risk_score", 0)
        over_privilege_score = score.get("over_privilege_score", 0)

        # Recommendation subtype
        rec_subtype = raw.get("recommenderSubtype", "N/A")

        # Add to user actions list
        user_actions.append(
            {
                "Account_Email": member,
                "Account_Type": account_type,
                "Project": project,
                "Current_Role": removed_role,
                "Recommendation": rec_subtype,
                "Description": description,
                "Total_Permissions": total_perms,
                "Used_Permissions": used_perms,
                "Unused_Permissions": total_perms - used_perms,
                "Waste_Percentage": round(waste_percentage, 1),
                "Risk_Score": risk_score,
                "Over_Privilege_Score": over_privilege_score,
                "Priority": raw.get("priority", "N/A"),
                "Exercised_Permissions": (
                    "; ".join(exercised_perms[:5]) if exercised_perms else "None"
                ),
            }
        )

        # Add to role analysis
        if removed_role != "N/A":
            role_usage_analysis[removed_role]["users"].add(member)
            role_usage_analysis[removed_role]["total_permissions"] = max(
                role_usage_analysis[removed_role]["total_permissions"], total_perms
            )
            role_usage_analysis[removed_role]["used_permissions"] = max(
                role_usage_analysis[removed_role]["used_permissions"], used_perms
            )
            role_usage_analysis[removed_role]["recommendations"].append(
                {"user": member, "waste_pct": waste_percentage, "exercised_perms": exercised_perms}
            )

    return user_actions, role_usage_analysis


def create_user_actions_csv(user_actions, filename="iam_recommendations_report.csv"):
    """Create CSV report of user actions needed."""

    print(f"Creating user actions report: {filename}")

    # Sort by waste percentage (highest first) and risk score
    user_actions.sort(key=lambda x: (x["Waste_Percentage"], x["Risk_Score"]), reverse=True)

    fieldnames = [
        "Account_Email",
        "Account_Type",
        "Project",
        "Current_Role",
        "Recommendation",
        "Description",
        "Total_Permissions",
        "Used_Permissions",
        "Unused_Permissions",
        "Waste_Percentage",
        "Risk_Score",
        "Over_Privilege_Score",
        "Priority",
        "Exercised_Permissions",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(user_actions)

    print(f"   Written {len(user_actions)} recommendations")


def create_role_analysis_csv(role_analysis, filename="role_analysis_report.csv"):
    """Create CSV report analyzing role usage patterns."""

    print(f"Creating role analysis report: {filename}")

    role_data = []
    for role, data in role_analysis.items():
        # Calculate average waste across users
        total_waste = sum(r["waste_pct"] for r in data["recommendations"])
        avg_waste = total_waste / len(data["recommendations"]) if data["recommendations"] else 0

        # Get most common exercised permissions
        all_exercised = []
        for r in data["recommendations"]:
            all_exercised.extend(r["exercised_perms"])

        # Count permission frequency
        perm_counts = defaultdict(int)
        for perm in all_exercised:
            perm_counts[perm] += 1

        # Get top 5 most used permissions
        top_perms = sorted(perm_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_perms_str = "; ".join([f"{perm}({count})" for perm, count in top_perms])

        role_data.append(
            {
                "Role_Name": role,
                "Affected_Users_Count": len(data["users"]),
                "Affected_Users": "; ".join(list(data["users"])[:3])
                + ("..." if len(data["users"]) > 3 else ""),
                "Total_Permissions": data["total_permissions"],
                "Max_Used_Permissions": data["used_permissions"],
                "Average_Waste_Percentage": round(avg_waste, 1),
                "Recommendation": "Create Custom Role" if avg_waste > 50 else "Review Usage",
                "Top_Used_Permissions": top_perms_str or "None",
                "Custom_Role_Suggestion": (
                    f"custom_{role.replace('roles/', '').replace('/', '_')}"
                    if avg_waste > 50
                    else "N/A"
                ),
            }
        )

    # Sort by average waste percentage
    role_data.sort(key=lambda x: x["Average_Waste_Percentage"], reverse=True)

    fieldnames = [
        "Role_Name",
        "Affected_Users_Count",
        "Affected_Users",
        "Total_Permissions",
        "Max_Used_Permissions",
        "Average_Waste_Percentage",
        "Recommendation",
        "Top_Used_Permissions",
        "Custom_Role_Suggestion",
    ]

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(role_data)

    print(f"   Written {len(role_data)} role analyses")


def main():
    json_file = "iam_recommendations_results.json"

    if not os.path.exists(json_file):
        print(f"Error: {json_file} not found!")
        return

    print("=" * 60)
    print("IAMSentry Recommendations Analyzer")
    print("=" * 60)

    # Analyze the recommendations
    user_actions, role_analysis = analyze_iam_recommendations(json_file)

    # Create reports
    create_user_actions_csv(user_actions)
    create_role_analysis_csv(role_analysis)

    # Summary statistics
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total recommendations: {len(user_actions)}")
    print(f"Unique roles analyzed: {len(role_analysis)}")

    # High waste roles (>50% unused permissions)
    high_waste_roles = [
        r
        for r in role_analysis.values()
        if sum(rec["waste_pct"] for rec in r["recommendations"]) / len(r["recommendations"]) > 50
    ]
    print(f"Roles with >50% permission waste: {len(high_waste_roles)}")

    # Users with high risk
    high_risk_users = [u for u in user_actions if u["Risk_Score"] > 50]
    print(f"High-risk user assignments: {len(high_risk_users)}")

    print("\nReports created:")
    print("- iam_recommendations_report.csv (User actions)")
    print("- role_analysis_report.csv (Role analysis & custom role suggestions)")
    print("=" * 60)


if __name__ == "__main__":
    main()
