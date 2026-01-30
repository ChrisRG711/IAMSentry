#!/usr/bin/env python3
import json
import sys
from collections import defaultdict

def analyze_service_accounts(json_file):
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    # Store service account info
    service_accounts = defaultdict(lambda: {
        'current_roles': set(),
        'recommended_roles': set(),
        'removed_roles': set(),
        'used_permissions': set(),
        'total_permissions': 0,
        'used_permission_count': 0,
        'insights': [],
        'recommendation_type': set()
    })
    
    # Process each recommendation
    for item in data:
        if 'raw' in item and 'content' in item['raw']:
            content = item['raw']['content']
            
            # Check overview for member info
            if 'overview' in content and 'member' in content['overview']:
                member = content['overview']['member']
                
                # Only process service accounts
                if member.startswith('serviceAccount:'):
                    sa_email = member.replace('serviceAccount:', '')
                    
                    # Get removed role from overview
                    if 'removedRole' in content['overview']:
                        removed_role = content['overview']['removedRole']
                        service_accounts[sa_email]['removed_roles'].add(removed_role)
                        service_accounts[sa_email]['current_roles'].add(removed_role)  # It was assigned
                    
                    # Get recommendation type
                    if 'recommenderSubtype' in item['raw']:
                        service_accounts[sa_email]['recommendation_type'].add(item['raw']['recommenderSubtype'])
                    
                    # Store insight description
                    if 'description' in item['raw']:
                        service_accounts[sa_email]['insights'].append(item['raw']['description'])
        
        # Also check insights data if present
        if 'insights' in item:
            for insight in item['insights']:
                if 'content' in insight and 'member' in insight['content']:
                    member = insight['content']['member']
                    
                    if member.startswith('serviceAccount:'):
                        sa_email = member.replace('serviceAccount:', '')
                        
                        # Get current role
                        if 'role' in insight['content']:
                            current_role = insight['content']['role']
                            service_accounts[sa_email]['current_roles'].add(current_role)
                        
                        # Get exercised permissions
                        if 'exercisedPermissions' in insight['content']:
                            for perm in insight['content']['exercisedPermissions']:
                                if 'permission' in perm:
                                    service_accounts[sa_email]['used_permissions'].add(perm['permission'])
                        
                        # Get account-level stats
                        if 'account_total_permissions' in insight:
                            service_accounts[sa_email]['total_permissions'] = insight['account_total_permissions']
                        if 'account_used_permissions' in insight:
                            service_accounts[sa_email]['used_permission_count'] = insight['account_used_permissions']
    
    return service_accounts

def categorize_service_account(sa_email):
    """Categorize service account by name patterns to understand intent"""
    sa_name = sa_email.split('@')[0]
    
    if 'gitlab' in sa_name:
        return 'CI/CD - GitLab'
    elif any(x in sa_name for x in ['gsa-', 'app', 'documo', 'portal']):
        return 'Application Service'
    elif any(x in sa_name for x in ['bucket', 'gcs', 'storage']):
        return 'Storage Management'
    elif any(x in sa_name for x in ['workstation', 'devops']):
        return 'Development/DevOps'
    elif any(x in sa_name for x in ['cloud-sql', 'sql']):
        return 'Database Management'
    elif any(x in sa_name for x in ['secret', 'gsm']):
        return 'Secret Management'
    elif any(x in sa_name for x in ['staging', 'prod']):
        return 'Environment-Specific'
    elif any(x in sa_name for x in ['monitoring', 'grafana', 'datadog', 'tenable']):
        return 'Monitoring/Security'
    elif any(x in sa_name for x in ['compute', 'gke', 'container']):
        return 'Infrastructure/Compute'
    elif any(x in sa_name for x in ['firebase', 'cloud-functions']):
        return 'Serverless/Functions'
    else:
        return 'Other/Unknown'

def recommend_optimized_roles(sa_email, sa_data, category):
    """Recommend optimized roles based on category and usage"""
    current_roles = sa_data['current_roles']
    used_permissions = sa_data['used_permissions']
    
    recommendations = {
        'keep_roles': set(),
        'remove_roles': set(),
        'replace_with': set(),
        'custom_role_needed': False,
        'rationale': []
    }
    
    # Analyze based on category
    if category == 'CI/CD - GitLab':
        # GitLab typically needs artifact registry, cloud build, GKE access
        essential_patterns = ['artifactregistry', 'cloudbuild', 'gkehub', 'iam.workloadIdentity']
        for role in current_roles:
            if any(pattern in role for pattern in essential_patterns):
                recommendations['keep_roles'].add(role)
                recommendations['rationale'].append(f"Keep {role} - Essential for CI/CD")
            elif 'admin' in role:
                recommendations['remove_roles'].add(role)
                recommendations['rationale'].append(f"Remove {role} - Too broad for automated deployment")
    
    elif category == 'Application Service':
        # Apps typically need limited compute, storage, and secrets access
        safe_patterns = ['secretmanager.secretAccessor', 'storage.objectUser', 'cloudsql.client']
        for role in current_roles:
            if any(pattern in role for pattern in safe_patterns):
                recommendations['keep_roles'].add(role)
            elif 'admin' in role:
                recommendations['remove_roles'].add(role)
                recommendations['rationale'].append(f"Remove {role} - Admin access not needed for apps")
    
    elif category == 'Storage Management':
        # Storage SAs should have storage-specific roles only
        for role in current_roles:
            if 'storage' in role:
                recommendations['keep_roles'].add(role)
            else:
                recommendations['remove_roles'].add(role)
                recommendations['rationale'].append(f"Remove {role} - Not storage-related")
    
    elif category == 'Database Management':
        # DB SAs should have SQL-specific roles only
        for role in current_roles:
            if 'sql' in role or 'cloudsql' in role:
                recommendations['keep_roles'].add(role)
            else:
                recommendations['remove_roles'].add(role)
                recommendations['rationale'].append(f"Remove {role} - Not database-related")
    
    elif category == 'Secret Management':
        # Secret SAs should have secret manager roles only
        for role in current_roles:
            if 'secret' in role:
                recommendations['keep_roles'].add(role)
            else:
                recommendations['remove_roles'].add(role)
                recommendations['rationale'].append(f"Remove {role} - Not secret-related")
    
    elif category == 'Monitoring/Security':
        # Monitoring needs read-only access typically
        for role in current_roles:
            if any(x in role for x in ['viewer', 'reader', 'monitoring']):
                recommendations['keep_roles'].add(role)
            elif 'admin' in role or 'editor' in role:
                recommendations['remove_roles'].add(role)
                recommendations['rationale'].append(f"Remove {role} - Read-only access sufficient for monitoring")
    
    # If we have used permissions but removing roles, suggest custom role
    if used_permissions and recommendations['remove_roles']:
        recommendations['custom_role_needed'] = True
        recommendations['rationale'].append("Consider custom role with only used permissions")
    
    return recommendations

def generate_report(service_accounts):
    print("# Service Account IAM Analysis Report")
    print("=" * 60)
    
    # Group by category
    categories = defaultdict(list)
    for sa_email, sa_data in service_accounts.items():
        category = categorize_service_account(sa_email)
        categories[category].append((sa_email, sa_data))
    
    for category, accounts in categories.items():
        print(f"\n## {category}")
        print("-" * 40)
        
        for sa_email, sa_data in accounts:
            print(f"\n### {sa_email}")
            print(f"**Current Roles:** {len(sa_data['current_roles'])}")
            for role in sorted(sa_data['current_roles']):
                print(f"  - {role}")
            
            print(f"**Permission Usage:** {sa_data['used_permission_count']}/{sa_data['total_permissions']} permissions used")
            
            if sa_data['used_permissions']:
                print("**Used Permissions:**")
                for perm in sorted(sa_data['used_permissions']):
                    print(f"  - {perm}")
            
            # Generate recommendations
            recommendations = recommend_optimized_roles(sa_email, sa_data, category)
            
            if recommendations['keep_roles'] or recommendations['remove_roles']:
                print("**Recommendations:**")
                for rationale in recommendations['rationale']:
                    print(f"  - {rationale}")
                
                if recommendations['keep_roles']:
                    print("  **Keep:**")
                    for role in sorted(recommendations['keep_roles']):
                        print(f"    - {role}")
                
                if recommendations['remove_roles']:
                    print("  **Remove:**")
                    for role in sorted(recommendations['remove_roles']):
                        print(f"    - {role}")
                
                if recommendations['custom_role_needed']:
                    print("  **Consider Custom Role:** Yes")

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "iam_recommendations_results.json"
    
    print("Analyzing service accounts from:", json_file)
    service_accounts = analyze_service_accounts(json_file)
    
    print(f"\nFound {len(service_accounts)} service accounts")
    generate_report(service_accounts)