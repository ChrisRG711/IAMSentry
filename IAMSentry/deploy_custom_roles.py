#!/usr/bin/env python3
"""
Deploy Custom IAM Roles to GCP Project
Usage: python deploy_custom_roles.py
"""

import os
import yaml
import json
import subprocess
from pathlib import Path

def load_role_definition(yaml_file):
    """Load a custom role definition from YAML."""
    with open(yaml_file, 'r') as f:
        return yaml.safe_load(f)

def create_gcp_role_json(role_def, role_id):
    """Convert YAML role definition to GCP role JSON format."""
    return {
        "roleId": role_id,
        "role": {
            "title": role_def.get('title', role_id),
            "description": role_def.get('description', ''),
            "stage": role_def.get('stage', 'GA'),
            "includedPermissions": role_def.get('includedPermissions', [])
        }
    }

def deploy_role(project_id, role_def, role_id):
    """Deploy a custom role to GCP project."""
    
    print(f"Creating role: {role_id}")
    print(f"  Title: {role_def['title']}")
    print(f"  Permissions: {len(role_def['includedPermissions'])}")
    
    # Create the gcloud command
    gcp_role = create_gcp_role_json(role_def, role_id)
    
    # Save to temp file
    temp_file = f"temp_{role_id}.json"
    with open(temp_file, 'w') as f:
        json.dump(gcp_role, f, indent=2)
    
    try:
        # Try to create the role
        cmd = [
            'gcloud', 'iam', 'roles', 'create', role_id,
            '--project', project_id,
            '--file', temp_file,
            '--quiet'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"  ✅ Successfully created role: {role_id}")
        else:
            # If role already exists, try to update it
            if "already exists" in result.stderr:
                print(f"  ℹ️  Role exists, updating: {role_id}")
                cmd[3] = 'update'  # Change 'create' to 'update'
                update_result = subprocess.run(cmd, capture_output=True, text=True)
                if update_result.returncode == 0:
                    print(f"  ✅ Successfully updated role: {role_id}")
                else:
                    print(f"  ❌ Failed to update role: {role_id}")
                    print(f"     Error: {update_result.stderr}")
            else:
                print(f"  ❌ Failed to create role: {role_id}")
                print(f"     Error: {result.stderr}")
    
    except Exception as e:
        print(f"  ❌ Exception creating role {role_id}: {e}")
    
    finally:
        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)

def generate_role_mapping_report():
    """Generate a report showing old role -> new role mappings."""
    
    mappings = [
        {
            'old_role': 'roles/container.admin',
            'new_role': 'projects/foiply-app/roles/custom_container_viewer',
            'permission_reduction': '429 -> ~15 permissions (96% reduction)',
            'affected_accounts': ['gsa-fusion-staging', 'gsa-fusion', 'dan-kott-workstation', 'gsa-portal']
        },
        {
            'old_role': 'roles/compute.viewer', 
            'new_role': 'projects/foiply-app/roles/custom_compute_monitor',
            'permission_reduction': '354 -> ~20 permissions (94% reduction)',
            'affected_accounts': ['datadog-118', 'tenable-io']
        },
        {
            'old_role': 'roles/secretmanager.admin',
            'new_role': 'projects/foiply-app/roles/custom_secret_reader', 
            'permission_reduction': '27 -> ~5 permissions (81% reduction)',
            'affected_accounts': ['devops-workstations', 'documo-devops-gsm']
        },
        {
            'old_role': 'roles/storage.objectAdmin',
            'new_role': 'projects/foiply-app/roles/custom_storage_reader',
            'permission_reduction': '28 -> ~10 permissions (64% reduction)', 
            'affected_accounts': ['cloud-sql', 'foiply-app@appspot']
        },
        {
            'old_role': 'roles/monitoring.metricWriter',
            'new_role': 'projects/foiply-app/roles/custom_monitoring_writer',
            'permission_reduction': '6 -> ~8 permissions (minimal increase for functionality)',
            'affected_accounts': ['collector', 'gsa-documo-staging', 'gsa-faxengine-staging']
        },
        {
            'old_role': 'roles/iam.serviceAccountUser',
            'new_role': 'projects/foiply-app/roles/custom_service_account_user',
            'permission_reduction': '5 -> ~3 permissions (40% reduction)',
            'affected_accounts': ['ubuntu-workstation', 'openemr-787']
        }
    ]
    
    print("\n" + "="*80)
    print("ROLE MIGRATION MAPPING")
    print("="*80)
    
    for mapping in mappings:
        print(f"\n📋 {mapping['old_role']}")
        print(f"   ➡️  {mapping['new_role']}")
        print(f"   🔒 {mapping['permission_reduction']}")
        print(f"   👥 Affected: {', '.join(mapping['affected_accounts'])}")
    
    print(f"\n{'='*80}")

def main():
    project_id = 'foiply-app'
    custom_roles_dir = Path('custom_roles')
    
    print("="*60)
    print("GCP Custom IAM Roles Deployment")
    print("="*60)
    print(f"Project: {project_id}")
    print(f"Roles directory: {custom_roles_dir}")
    
    if not custom_roles_dir.exists():
        print(f"❌ Directory {custom_roles_dir} not found!")
        return
    
    # Find all YAML files
    yaml_files = list(custom_roles_dir.glob('*.yaml'))
    
    if not yaml_files:
        print(f"❌ No YAML files found in {custom_roles_dir}")
        return
    
    print(f"Found {len(yaml_files)} custom role definitions")
    print("-"*60)
    
    # Deploy each role
    for yaml_file in yaml_files:
        role_id = yaml_file.stem  # filename without extension
        
        try:
            role_def = load_role_definition(yaml_file)
            deploy_role(project_id, role_def, role_id)
        except Exception as e:
            print(f"❌ Error processing {yaml_file}: {e}")
        
        print("-"*60)
    
    # Generate migration report
    generate_role_mapping_report()
    
    print("\n🎯 NEXT STEPS:")
    print("1. Review the custom roles created above")
    print("2. Test the custom roles with a few service accounts first")
    print("3. Use the role mapping to update service account bindings")
    print("4. Monitor applications for any permission issues")
    print("5. Remove old over-privileged role bindings after testing")

if __name__ == '__main__':
    main()