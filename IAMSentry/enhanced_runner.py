#!/usr/bin/env python3
"""
Enhanced IAMSentry runner with IAM remediation capabilities
Extends the existing IAMSentry workflow with optional remediation actions
"""

import os
import sys
import json
import argparse
from datetime import datetime

def main():
    parser = argparse.ArgumentParser(description='IAMSentry - Enhanced IAM Analysis and Remediation')
    parser.add_argument('config_file', nargs='?', default='../enhanced_config_example.yaml',
                       help='Configuration file (default: enhanced_config_example.yaml)')
    
    # Analysis options (existing)
    parser.add_argument('--analyze-only', action='store_true', 
                       help='Run analysis only (default behavior)')
    
    # NEW: Remediation options
    parser.add_argument('--remediation-mode', choices=['analyze', 'dry-run', 'execute'], 
                       default='analyze',
                       help='Remediation mode: analyze=plan only, dry-run=simulate, execute=apply changes')
    
    parser.add_argument('--auto-create-roles', action='store_true',
                       help='Automatically create custom roles if they don\'t exist')
    
    parser.add_argument('--max-changes', type=int, default=10,
                       help='Maximum number of remediation changes per run (safety limit)')
    
    parser.add_argument('--priority-filter', choices=['critical', 'high', 'medium', 'low'],
                       help='Only remediate findings above this priority level')
    
    # Reporting options  
    parser.add_argument('--generate-remediation-plan', action='store_true',
                       help='Generate detailed remediation execution plan')
    
    parser.add_argument('--generate-custom-roles', action='store_true',
                       help='Generate custom role YAML files from analysis')
    
    args = parser.parse_args()
    
    # Add parent directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    
    print("=" * 70)
    print("🚀 IAMSentry Enhanced - IAM Analysis & Remediation Platform")
    print("=" * 70)
    print(f"📋 Config: {args.config_file}")
    print(f"🔧 Remediation Mode: {args.remediation_mode}")
    print(f"📊 Max Changes: {args.max_changes}")
    
    if args.remediation_mode != 'analyze':
        print("⚠️  REMEDIATION MODE ENABLED - Changes will be made to your GCP project!")
        if args.remediation_mode == 'execute':
            print("🚨 EXECUTE MODE - ACTUAL CHANGES WILL BE APPLIED!")
            confirm = input("Type 'yes' to confirm: ")
            if confirm.lower() != 'yes':
                print("❌ Aborted by user")
                return 1
    
    print("-" * 70)
    
    try:
        # Load configuration
        from IAMSentry.helpers.hconfigs import Config
        config = Config.load(args.config_file)
        
        # Initialize plugins based on mode
        results = run_enhanced_analysis(config, args)
        
        # Generate additional reports if requested
        if args.generate_remediation_plan:
            generate_remediation_plan(results)
            
        if args.generate_custom_roles:
            generate_custom_role_files(results)
        
        print_summary(results, args)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

def run_enhanced_analysis(config, args):
    """Run the enhanced IAMSentry analysis with optional remediation"""
    
    print("📡 Initializing IAMSentry components...")
    
    # Initialize existing components
    from IAMSentry.plugins.gcp.gcpcloud import GCPCloudIAMRecommendations
    from IAMSentry.plugins.gcp.gcpcloudiam import GCPIAMRecommendationProcessor
    
    # Initialize new remediation component
    try:
        from IAMSentry.plugins.gcp.gcpiam_remediation import GCPIAMRemediationProcessor
        remediation_available = True
    except ImportError:
        print("⚠️  Remediation plugin not available - running analysis only")
        remediation_available = False
    
    # Get configurations
    reader_config = config['plugins']['gcp_iam_reader']
    processor_config = config['plugins']['gcp_iam_processor']
    
    # Setup reader
    reader_params = {
        'key_file_path': reader_config['key_file_path'],
        'projects': reader_config.get('projects', ['foiply-app']),
        'processes': 1,
        'threads': 1
    }
    reader = GCPCloudIAMRecommendations(**reader_params)
    
    # Setup processor
    processor_params = {
        'mode_scan': processor_config.get('mode_scan', True),
        'mode_enforce': processor_config.get('mode_enforce', False),
        'enforcer': processor_config.get('enforcer', None)
    }
    processor = GCPIAMRecommendationProcessor(**processor_params)
    
    # Setup remediation processor if available and requested
    remediation_processor = None
    if remediation_available and args.remediation_mode != 'analyze':
        remediation_config = config['plugins'].get('gcp_iam_remediation', {})
        
        remediation_params = {
            'mode_remediate': True,
            'dry_run': args.remediation_mode != 'execute',
            'remediation_config': {
                'max_changes_per_run': args.max_changes,
                'auto_create_custom_roles': args.auto_create_roles,
                **remediation_config.get('remediation_config', {})
            }
        }
        remediation_processor = GCPIAMRemediationProcessor(**remediation_params)
        print(f"🔧 Remediation processor initialized - Mode: {args.remediation_mode}")
    
    # Process recommendations
    print("📊 Processing IAM recommendations...")
    results = []
    count = 0
    
    for record in reader.read():
        count += 1
        print(f"   Processing recommendation {count}...")
        
        # Run through analysis processor
        for analyzed_record in processor.eval(record):
            
            # Run through remediation processor if available
            if remediation_processor:
                for enhanced_record in remediation_processor.eval(analyzed_record):
                    # Apply priority filter if specified
                    if args.priority_filter:
                        remediation = enhanced_record.get('remediation', {})
                        if remediation.get('priority', 'low') != args.priority_filter:
                            continue
                    results.append(enhanced_record)
            else:
                results.append(analyzed_record)
    
    # Cleanup
    reader.done()
    processor.done()
    if remediation_processor:
        remediation_processor.done()
    
    # Save enhanced results
    output_file = f"enhanced_iam_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"📁 Results saved to: {output_file}")
    
    return results

def generate_remediation_plan(results):
    """Generate detailed remediation execution plan"""
    print("\n📋 Generating remediation execution plan...")
    
    plan_data = []
    for result in results:
        remediation = result.get('remediation')
        if remediation and remediation.get('recommended_action') != 'no_action':
            plan_data.append({
                'account': remediation.get('account_id'),
                'current_role': remediation.get('current_role'),
                'action': remediation.get('recommended_action'),
                'custom_role': remediation.get('custom_role_suggestion'),
                'priority': remediation.get('priority'),
                'waste_percentage': remediation.get('waste_percentage'),
                'safety_checks': remediation.get('safety_checks', [])
            })
    
    # Sort by priority
    priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    plan_data.sort(key=lambda x: priority_order.get(x['priority'], 99))
    
    # Save plan
    plan_file = f"remediation_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(plan_file, 'w') as f:
        json.dump(plan_data, f, indent=2, default=str)
    
    print(f"📁 Remediation plan saved to: {plan_file}")
    return plan_data

def generate_custom_role_files(results):
    """Generate custom role YAML files based on analysis"""
    print("\n🔧 Generating custom role files...")
    
    # This would analyze the results and generate optimized custom roles
    # based on actual permission usage patterns
    print("   (Custom role generation from usage patterns - future feature)")
    
def print_summary(results, args):
    """Print summary of analysis and remediation actions"""
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    total_recommendations = len(results)
    print(f"Total IAM recommendations analyzed: {total_recommendations}")
    
    if args.remediation_mode != 'analyze':
        # Count remediation actions
        actions = {'remove_binding': 0, 'migrate_to_custom_role': 0, 'review_manual': 0, 'no_action': 0}
        priorities = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
        
        for result in results:
            remediation = result.get('remediation', {})
            action = remediation.get('recommended_action', 'no_action')
            priority = remediation.get('priority', 'low')
            
            actions[action] = actions.get(action, 0) + 1
            priorities[priority] = priorities.get(priority, 0) + 1
        
        print(f"\nRemediation Actions Planned:")
        for action, count in actions.items():
            if count > 0:
                print(f"  {action.replace('_', ' ').title()}: {count}")
        
        print(f"\nPriority Distribution:")
        for priority, count in priorities.items():
            if count > 0:
                print(f"  {priority.title()}: {count}")
        
        if args.remediation_mode == 'dry-run':
            print(f"\n🔍 Mode: DRY RUN - No actual changes made")
        elif args.remediation_mode == 'execute':
            print(f"\n⚡ Mode: EXECUTE - Changes applied to GCP")
    
    print("=" * 70)

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
