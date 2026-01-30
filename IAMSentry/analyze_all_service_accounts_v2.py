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
        'removed_roles': set(),
        'used_permissions': set(),
        'total_permissions': 0,
        'used_permission_count': 0,
        'insights': [],
        'recommendation_types': set(),
        'usage_descriptions': []
    })
    
    # Process each item in the JSON
    for item in data:
        # Extract service account from account_id field
        if 'account_id' in item and '@' in item['account_id']:
            sa_email = item['account_id']
            
            # Get account-level stats
            if 'account_total_permissions' in item:
                service_accounts[sa_email]['total_permissions'] = item['account_total_permissions']
            if 'account_used_permissions' in item:
                service_accounts[sa_email]['used_permission_count'] = item['account_used_permissions']
            
            # Get recommendation type
            if 'recommendetion_recommender_subtype' in item:
                service_accounts[sa_email]['recommendation_types'].add(item['recommendetion_recommender_subtype'])
        
        # Extract from raw.content.overview if present
        if 'raw' in item and 'content' in item['raw'] and 'overview' in item['raw']['content']:
            overview = item['raw']['content']['overview']
            if 'member' in overview and overview['member'].startswith('serviceAccount:'):
                sa_email = overview['member'].replace('serviceAccount:', '')
                
                # Get removed role
                if 'removedRole' in overview:
                    removed_role = overview['removedRole']
                    service_accounts[sa_email]['removed_roles'].add(removed_role)
                    service_accounts[sa_email]['current_roles'].add(removed_role)  # It was assigned
                
                # Get recommendation type
                if 'recommenderSubtype' in item['raw']:
                    service_accounts[sa_email]['recommendation_types'].add(item['raw']['recommenderSubtype'])
                
                # Store description
                if 'description' in item['raw']:
                    service_accounts[sa_email]['usage_descriptions'].append(item['raw']['description'])
        
        # Extract from insights array
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
                        
                        # Store insight description
                        if 'description' in insight:
                            service_accounts[sa_email]['usage_descriptions'].append(insight['description'])
    
    return service_accounts

def categorize_service_account(sa_email):
    """Categorize service account by name patterns to understand intent"""
    sa_name = sa_email.split('@')[0].lower()
    
    if 'gitlab' in sa_name:
        return 'CI/CD - GitLab'
    elif any(x in sa_name for x in ['gsa-', 'app', 'documo', 'portal']):
        return 'Application Service'
    elif any(x in sa_name for x in ['bucket', 'gcs', 'storage']):
        return 'Storage Management'
    elif any(x in sa_name for x in ['workstation', 'devops']):
        return 'Development/DevOps'
    elif any(x in sa_name for x in ['cloud-sql', 'sql', 'cloudsql']):
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
    elif any(x in sa_name for x in ['cert-manager']):
        return 'Certificate Management'
    elif any(x in sa_name for x in ['collector']):
        return 'Data Collection'
    elif any(x in sa_name for x in ['sftp', 'fax']):
        return 'File Transfer/Communication'
    else:
        return 'Other/Unknown'

def get_role_intent(role_name):
    """Determine the likely intent behind a role assignment"""
    role = role_name.lower()
    
    if 'admin' in role:
        return 'Administrative Access'
    elif 'editor' in role:
        return 'Read/Write Access'
    elif 'viewer' in role or 'reader' in role:
        return 'Read-Only Access'
    elif 'user' in role:
        return 'Standard User Access'
    elif 'secretmanager' in role:
        return 'Secret Management'
    elif 'storage' in role:
        return 'Storage Operations'
    elif 'compute' in role:
        return 'Compute Resources'
    elif 'cloudbuild' in role:
        return 'CI/CD Build Operations'
    elif 'artifactregistry' in role:
        return 'Container/Artifact Management'
    elif 'gkehub' in role:
        return 'GKE Cluster Management'
    elif 'iam' in role:
        return 'Identity Management'
    elif 'monitoring' in role:
        return 'Monitoring/Observability'
    else:
        return 'Specialized Function'

def recommend_optimized_roles(sa_email, sa_data, category):
    """Recommend optimized roles based on category and usage"""
    current_roles = sa_data['current_roles']
    removed_roles = sa_data['removed_roles']
    used_permissions = sa_data['used_permissions']
    
    recommendations = {
        'keep_roles': set(),
        'remove_roles': set(),
        'replace_with': set(),
        'custom_role_needed': False,
        'rationale': []
    }
    
    # Start with the removed roles - these are what Google recommends removing
    recommendations['remove_roles'] = removed_roles.copy()
    
    # Roles to keep = current roles - removed roles
    recommendations['keep_roles'] = current_roles - removed_roles
    
    # Add specific recommendations based on category
    if category == 'CI/CD - GitLab':
        # For GitLab, if we're removing broad admin roles, suggest specific alternatives
        if any('admin' in role for role in removed_roles):
            recommendations['replace_with'].update([
                'roles/artifactregistry.writer',
                'roles/cloudbuild.builds.editor',
                'roles/container.developer',
                'roles/iam.workloadIdentityUser'
            ])
            recommendations['rationale'].append("Replace admin roles with specific CI/CD permissions")
    
    elif category == 'Application Service':
        # Apps should have minimal permissions
        if any('admin' in role for role in removed_roles):
            recommendations['replace_with'].update([
                'roles/secretmanager.secretAccessor',
                'roles/storage.objectUser',
                'roles/cloudsql.client'
            ])
            recommendations['rationale'].append("Replace admin roles with application-specific permissions")
    
    elif category == 'Monitoring/Security':
        # Monitoring should be read-only
        if any(x in role for role in removed_roles for x in ['admin', 'editor']):
            recommendations['replace_with'].update([
                'roles/monitoring.viewer',
                'roles/logging.viewer'
            ])
            recommendations['rationale'].append("Use read-only roles for monitoring")
    
    # If we have specific used permissions, suggest custom role
    if used_permissions and len(used_permissions) < 20:  # Not too many permissions
        recommendations['custom_role_needed'] = True
        recommendations['rationale'].append(f"Consider custom role with {len(used_permissions)} specific used permissions")
    
    return recommendations

def generate_report(service_accounts):
    print("# Service Account IAM Optimization Report")
    print("=" * 60)
    print(f"Analyzed {len(service_accounts)} service accounts")
    
    # Summary statistics
    total_roles = sum(len(sa_data['current_roles']) for sa_data in service_accounts.values())
    total_removed = sum(len(sa_data['removed_roles']) for sa_data in service_accounts.values())
    
    print(f"Total current role assignments: {total_roles}")
    print(f"Total recommended removals: {total_removed}")
    print(f"Potential reduction: {total_removed/total_roles*100:.1f}%")
    
    # Group by category
    categories = defaultdict(list)
    for sa_email, sa_data in service_accounts.items():
        category = categorize_service_account(sa_email)
        categories[category].append((sa_email, sa_data))
    
    for category, accounts in sorted(categories.items()):
        print(f"\n## {category} ({len(accounts)} accounts)")
        print("-" * 50)
        
        for sa_email, sa_data in sorted(accounts):
            print(f"\n### {sa_email}")
            
            # Current state
            if sa_data['current_roles']:
                print(f"**Current Roles ({len(sa_data['current_roles'])}):**")
                for role in sorted(sa_data['current_roles']):
                    intent = get_role_intent(role)
                    print(f"  - {role} ({intent})")
            
            # Usage stats
            total_perms = sa_data['total_permissions']
            used_perms = sa_data['used_permission_count']
            if total_perms > 0:
                usage_pct = (used_perms / total_perms) * 100
                print(f"**Permission Usage:** {used_perms}/{total_perms} ({usage_pct:.1f}%)")
            
            # Specific used permissions
            if sa_data['used_permissions']:
                print(f"**Actually Used Permissions ({len(sa_data['used_permissions'])}):**")
                for perm in sorted(sa_data['used_permissions']):
                    print(f"  - {perm}")
            
            # Generate recommendations
            recommendations = recommend_optimized_roles(sa_email, sa_data, category)
            
            if recommendations['remove_roles']:
                print("**RECOMMENDED REMOVALS:**")
                for role in sorted(recommendations['remove_roles']):
                    intent = get_role_intent(role)
                    print(f"  - {role} ({intent})")
            
            if recommendations['keep_roles']:
                print("**KEEP THESE ROLES:**")
                for role in sorted(recommendations['keep_roles']):
                    intent = get_role_intent(role)
                    print(f"  - {role} ({intent})")
            
            if recommendations['replace_with']:
                print("**SUGGESTED REPLACEMENTS:**")
                for role in sorted(recommendations['replace_with']):
                    intent = get_role_intent(role)
                    print(f"  - {role} ({intent})")
            
            if recommendations['custom_role_needed']:
                print("**CUSTOM ROLE OPPORTUNITY:** Yes")
                print(f"   Create role with {len(sa_data['used_permissions'])} specific permissions")
            
            # Usage insights
            if sa_data['usage_descriptions']:
                unique_descriptions = set(sa_data['usage_descriptions'])
                print("**Usage Analysis:**")
                for desc in unique_descriptions:
                    print(f"  - {desc}")

if __name__ == "__main__":
    json_file = sys.argv[1] if len(sys.argv) > 1 else "iam_recommendations_results.json"
    
    print("Analyzing service accounts from:", json_file)
    service_accounts = analyze_service_accounts(json_file)
    generate_report(service_accounts)