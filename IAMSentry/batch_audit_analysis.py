#!/usr/bin/env python3
"""
Batch analyzer for multiple service accounts using audit logs
Includes rate limiting and progress tracking
"""

import json
import sys
import time

from audit_log_permission_analyzer import AuditLogPermissionAnalyzer


def load_service_accounts_from_analysis(analysis_file):
    """Extract service accounts from our previous analysis"""

    service_accounts = set()

    try:
        with open(analysis_file, "r") as f:
            data = json.load(f)

        for item in data:
            if "account_id" in item and "account_type" in item:
                if item["account_type"] == "serviceAccount" and "@" in item["account_id"]:
                    service_accounts.add(item["account_id"])

    except Exception as e:
        print(f"Error loading analysis file: {e}")
        return []

    return sorted(list(service_accounts))


def main():
    project_id = "your-gcp-project-id"  # Replace with your GCP project ID
    days_back = 400  # Use full audit log retention
    rate_limit_delay = 3  # 3 seconds between queries to avoid rate limiting

    # Priority service accounts to analyze first (replace with your service accounts)
    priority_accounts = [
        "123456789-compute@developer.gserviceaccount.com",
        "cicd-runner@your-project.iam.gserviceaccount.com",
        "app-service@your-project.iam.gserviceaccount.com",
    ]

    # Load all service accounts from our analysis
    print("Loading service accounts from analysis...")
    if len(sys.argv) > 1:
        analysis_file = sys.argv[1]
    else:
        analysis_file = "fresh_iam_recommendations_results.json"

    all_accounts = load_service_accounts_from_analysis(analysis_file)
    print(f"Found {len(all_accounts)} service accounts to analyze")

    # Prioritize important accounts
    accounts_to_analyze = []
    for priority_account in priority_accounts:
        if priority_account in all_accounts:
            accounts_to_analyze.append(priority_account)
            all_accounts.remove(priority_account)

    # Add remaining accounts
    accounts_to_analyze.extend(all_accounts)

    print(
        f"\nAnalyzing {len(accounts_to_analyze)} service accounts with {days_back}-day lookback..."
    )
    print(f"Rate limiting: {rate_limit_delay} seconds between queries")
    print("\nPriority accounts will be analyzed first:")
    for acc in priority_accounts:
        if acc in accounts_to_analyze:
            print(f"  🔸 {acc}")

    # Initialize analyzer
    analyzer = AuditLogPermissionAnalyzer(project_id, rate_limit_delay)

    # Store all results
    all_results = []
    failed_accounts = []

    # Analyze each account
    for i, account in enumerate(accounts_to_analyze, 1):
        print(f"\n\n📋 Progress: {i}/{len(accounts_to_analyze)}")

        try:
            result = analyzer.analyze_service_account(account, days_back)
            all_results.append(result)

            # Quick summary for tracking
            if result["status"] == "success":
                print(
                    f"✅ {account}: {result['total_api_calls']} API calls, {len(result['permissions_used'])} permissions"
                )
            else:
                print(f"⚠️  {account}: No audit logs found")

        except Exception as e:
            print(f"❌ Error analyzing {account}: {e}")
            failed_accounts.append(account)

        # Rate limiting between accounts
        if i < len(accounts_to_analyze):  # Don't wait after the last one
            print(f"⏱️  Waiting {rate_limit_delay} seconds...")
            time.sleep(rate_limit_delay)

    # Save combined results
    output_file = f"batch_audit_analysis_results_{int(time.time())}.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    # Generate summary report
    summary_file = f"audit_analysis_summary_{int(time.time())}.md"
    generate_summary_report(all_results, failed_accounts, summary_file, days_back)

    print(f"\n🎉 Analysis Complete!")
    print(f"📄 Full results: {output_file}")
    print(f"📊 Summary report: {summary_file}")
    print(f"✅ Successful: {len([r for r in all_results if r['status'] == 'success'])}")
    print(f"⚠️  No logs: {len([r for r in all_results if r['status'] == 'no_logs_found'])}")
    print(f"❌ Failed: {len(failed_accounts)}")


def generate_summary_report(results, failed_accounts, output_file, days_back):
    """Generate a markdown summary report"""

    with open(output_file, "w") as f:
        f.write(f"# Audit Log Permission Analysis Summary\n")
        f.write(f"Analysis Period: {days_back} days\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Overall stats
        total_accounts = len(results)
        successful = [r for r in results if r["status"] == "success"]
        no_logs = [r for r in results if r["status"] == "no_logs_found"]

        f.write(f"## Summary Statistics\n")
        f.write(f"- Total accounts analyzed: {total_accounts}\n")
        f.write(f"- Accounts with audit logs: {len(successful)}\n")
        f.write(f"- Accounts with no logs: {len(no_logs)}\n")
        f.write(f"- Failed analyses: {len(failed_accounts)}\n\n")

        # Most active accounts
        if successful:
            f.write(f"## Most Active Service Accounts\n")
            active_accounts = sorted(successful, key=lambda x: x["total_api_calls"], reverse=True)[
                :10
            ]
            for account in active_accounts:
                f.write(
                    f"- **{account['service_account']}**: {account['total_api_calls']} API calls, "
                    f"{len(account['permissions_used'])} permissions\n"
                )
            f.write("\n")

        # Detailed results
        f.write(f"## Detailed Results\n\n")
        for result in sorted(results, key=lambda x: x.get("total_api_calls", 0), reverse=True):
            f.write(f"### {result['service_account']}\n")

            if result["status"] == "success":
                f.write(
                    f"- **Status**: ✅ Active (found {result['log_entries_found']} log entries)\n"
                )
                f.write(
                    f"- **API Calls**: {result['total_api_calls']} total, {result['unique_api_calls']} unique\n"
                )
                f.write(
                    f"- **Services Used**: {', '.join(result['services_used']) if result['services_used'] else 'None'}\n"
                )
                f.write(f"- **Estimated Permissions**: {len(result['permissions_used'])}\n")

                if result["permissions_used"]:
                    f.write(f"- **Key Permissions**:\n")
                    for perm in result["permissions_used"][:5]:
                        f.write(f"  - {perm}\n")

                if result["api_calls"]:
                    f.write(f"- **Top API Calls**:\n")
                    for api, count in list(result["api_calls"].items())[:3]:
                        f.write(f"  - {api}: {count}x\n")
            else:
                f.write(f"- **Status**: ⚠️ No audit logs found (possibly unused)\n")

            f.write("\n")

        # Failed accounts
        if failed_accounts:
            f.write(f"## Failed Analyses\n")
            for account in failed_accounts:
                f.write(f"- {account}\n")


if __name__ == "__main__":
    main()
