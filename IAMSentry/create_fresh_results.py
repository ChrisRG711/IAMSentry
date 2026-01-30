#!/usr/bin/env python3
"""
Script to combine fresh GCP IAM recommendations and insights into the same format
as the existing iam_recommendations_results.json file
"""

import json
import sys
from collections import defaultdict

def load_json_file(filepath):
    """Load JSON data from file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return []

def extract_member_from_path_filters(path_filters):
    """Extract member from pathFilters"""
    return path_filters.get('/iamPolicy/bindings/*/members/*', '')

def extract_role_from_path_filters(path_filters):
    """Extract role from pathFilters"""
    return path_filters.get('/iamPolicy/bindings/*/role', '')

def create_combined_results(recommendations_file, insights_file, output_file):
    """Combine recommendations and insights into unified format"""
    
    print(f"Loading recommendations from: {recommendations_file}")
    recommendations = load_json_file(recommendations_file)
    
    print(f"Loading insights from: {insights_file}")
    insights = load_json_file(insights_file)
    
    # Group insights by member for easy lookup
    insights_by_member = defaultdict(list)
    for insight in insights:
        if 'content' in insight and 'member' in insight['content']:
            member = insight['content']['member']
            insights_by_member[member].append(insight)
    
    # Create combined results
    combined_results = []
    
    for recommendation in recommendations:
        # Extract member info from recommendation
        member = ""
        if ('content' in recommendation and 
            'operationGroups' in recommendation['content']):
            for op_group in recommendation['content']['operationGroups']:
                for operation in op_group.get('operations', []):
                    if 'pathFilters' in operation:
                        member = extract_member_from_path_filters(operation['pathFilters'])
                        break
                if member:
                    break
        
        # Also check overview section
        if not member and 'content' in recommendation and 'overview' in recommendation['content']:
            member = recommendation['content']['overview'].get('member', '')
        
        # Create combined entry
        combined_entry = {
            'raw': recommendation,
            'insights': insights_by_member.get(member, [])
        }
        
        # Add account-level info if available
        if member:
            account_id = member.replace('serviceAccount:', '').replace('user:', '').replace('group:', '')
            combined_entry['account_id'] = account_id
            
            # Determine account type
            if member.startswith('serviceAccount:'):
                combined_entry['account_type'] = 'serviceAccount'
            elif member.startswith('user:'):
                combined_entry['account_type'] = 'user'
            elif member.startswith('group:'):
                combined_entry['account_type'] = 'group'
            else:
                combined_entry['account_type'] = 'unknown'
            
            # Add recommendation type
            combined_entry['recommendetion_recommender_subtype'] = recommendation.get('recommenderSubtype', '')
            
            # Calculate permission stats from insights
            total_permissions = 0
            used_permissions = 0
            
            for insight in insights_by_member.get(member, []):
                if 'content' in insight:
                    content = insight['content']
                    if 'currentTotalPermissionsCount' in content:
                        try:
                            total_permissions += int(content['currentTotalPermissionsCount'])
                        except:
                            pass
                    
                    if 'exercisedPermissions' in content:
                        used_permissions += len(content['exercisedPermissions'])
            
            combined_entry['account_total_permissions'] = total_permissions
            combined_entry['account_used_permissions'] = used_permissions
            combined_entry['account_permission_insights_category'] = 'SECURITY'
        
        combined_results.append(combined_entry)
    
    # Save combined results
    print(f"Saving combined results to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(combined_results, f, indent=2)
    
    print(f"Created combined results with {len(combined_results)} entries")
    
    # Print summary
    account_types = defaultdict(int)
    recommendation_types = defaultdict(int)
    
    for entry in combined_results:
        if 'account_type' in entry:
            account_types[entry['account_type']] += 1
        if 'recommendetion_recommender_subtype' in entry:
            recommendation_types[entry['recommendetion_recommender_subtype']] += 1
    
    print(f"\nSummary:")
    print(f"Account types: {dict(account_types)}")
    print(f"Recommendation types: {dict(recommendation_types)}")

if __name__ == "__main__":
    recommendations_file = "fresh_iam_recommendations.json"
    insights_file = "fresh_iam_insights.json"
    output_file = "fresh_iam_recommendations_results.json"
    
    if len(sys.argv) > 1:
        recommendations_file = sys.argv[1]
    if len(sys.argv) > 2:
        insights_file = sys.argv[2]
    if len(sys.argv) > 3:
        output_file = sys.argv[3]
    
    create_combined_results(recommendations_file, insights_file, output_file)