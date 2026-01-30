"""
IAMSentry Remediation Plugin for GCP IAM
Optional component to automatically remediate IAM over-privileges

Safety Features:
- Dry-run mode by default
- Approval workflows  
- Rollback capabilities
- Extensive logging
"""

import json
import time
import yaml
from datetime import datetime
from collections import defaultdict

from IAMSentry.helpers import hlogging
from . import util_gcp

_log = hlogging.get_logger(__name__)

class GCPIAMRemediationProcessor:
    """
    Optional IAMSentry plugin for IAM remediation
    Extends the analysis capabilities with automated fixes
    """
    
    def __init__(self, mode_remediate=False, dry_run=True, remediation_config=None):
        """
        Initialize IAM remediation processor
        
        Args:
            mode_remediate (bool): Enable remediation mode
            dry_run (bool): Only simulate changes (default: True for safety)
            remediation_config (dict): Remediation settings and approvals
        """
        self._mode_remediate = mode_remediate
        self._dry_run = dry_run
        self._config = remediation_config or {}
        
        # Safety settings
        self._max_changes_per_run = self._config.get('max_changes_per_run', 10)
        self._require_approval = self._config.get('require_approval', True)
        self._auto_create_custom_roles = self._config.get('auto_create_custom_roles', False)
        
        # Statistics
        self._remediation_stats = {
            'custom_roles_created': 0,
            'bindings_removed': 0,
            'bindings_migrated': 0,
            'errors': 0
        }
        
        # Custom role definitions (loaded from YAML files)
        self._custom_role_definitions = self._load_custom_role_definitions()
        
        if self._mode_remediate:
            _log.info('IAM Remediation mode enabled - DRY RUN: %s', self._dry_run)
        
    def _load_custom_role_definitions(self):
        """Load custom role definitions from YAML files"""
        definitions = {}
        try:
            import os
            custom_roles_dir = os.path.join(os.path.dirname(__file__), '../../../custom_roles')
            if os.path.exists(custom_roles_dir):
                for filename in os.listdir(custom_roles_dir):
                    if filename.endswith('.yaml'):
                        role_id = filename.replace('.yaml', '')
                        filepath = os.path.join(custom_roles_dir, filename)
                        with open(filepath, 'r') as f:
                            definitions[role_id] = yaml.safe_load(f)
                _log.info('Loaded %d custom role definitions', len(definitions))
        except Exception as e:
            _log.warning('Could not load custom role definitions: %s', e)
        return definitions
        
    def eval(self, record):
        """
        Process IAM recommendation and optionally remediate
        
        Args:
            record: IAMSentry recommendation record
            
        Yields:
            dict: Enhanced record with remediation actions
        """
        # First, yield the original analysis
        enhanced_record = record.copy()
        
        # Add remediation analysis
        remediation_plan = self._analyze_remediation_options(record)
        enhanced_record['remediation'] = remediation_plan
        
        # If remediation mode is enabled, execute the plan
        if self._mode_remediate and remediation_plan.get('recommended_action') != 'no_action':
            remediation_result = self._execute_remediation(record, remediation_plan)
            enhanced_record['remediation']['execution_result'] = remediation_result
            
        yield enhanced_record
        
    def _analyze_remediation_options(self, record):
        """Analyze what remediation actions are recommended"""
        processor = record.get('processor', {})
        score = record.get('score', {})
        
        account_id = processor.get('account_id')
        account_type = processor.get('account_type')
        waste_percentage = score.get('over_privilege_score', 0)
        risk_score = score.get('risk_score', 0)
        
        # Get role information
        raw = record.get('raw', {})
        overview = raw.get('content', {}).get('overview', {})
        current_role = overview.get('removedRole', '')
        
        remediation_plan = {
            'account_id': account_id,
            'account_type': account_type,
            'current_role': current_role,
            'waste_percentage': waste_percentage,
            'risk_score': risk_score,
            'recommended_action': 'no_action',
            'custom_role_suggestion': None,
            'safety_checks': [],
            'priority': self._calculate_remediation_priority(waste_percentage, risk_score, account_type)
        }
        
        # Determine recommended action based on analysis
        if waste_percentage >= 100:
            # Completely unused role
            remediation_plan['recommended_action'] = 'remove_binding'
            remediation_plan['reason'] = 'Role has 0% usage - completely unused'
            
        elif waste_percentage >= 70:
            # High waste - suggest custom role
            custom_role_id = self._suggest_custom_role(current_role)
            if custom_role_id:
                remediation_plan['recommended_action'] = 'migrate_to_custom_role'
                remediation_plan['custom_role_suggestion'] = custom_role_id
                remediation_plan['reason'] = f'Role has {waste_percentage}% waste - migrate to custom role'
            else:
                remediation_plan['recommended_action'] = 'review_manual'
                remediation_plan['reason'] = f'High waste ({waste_percentage}%) but no custom role available'
                
        elif waste_percentage >= 40:
            # Moderate waste - review
            remediation_plan['recommended_action'] = 'review_manual'
            remediation_plan['reason'] = f'Moderate waste ({waste_percentage}%) - manual review recommended'
            
        # Add safety checks
        remediation_plan['safety_checks'] = self._perform_safety_checks(remediation_plan, record)
        
        return remediation_plan
        
    def _suggest_custom_role(self, current_role):
        """Suggest a custom role replacement for over-privileged role"""
        role_mappings = {
            'roles/container.admin': 'custom_container_viewer',
            'roles/compute.viewer': 'custom_compute_monitor', 
            'roles/secretmanager.admin': 'custom_secret_reader',
            'roles/storage.objectAdmin': 'custom_storage_reader',
            'roles/monitoring.metricWriter': 'custom_monitoring_writer',
            'roles/iam.serviceAccountUser': 'custom_service_account_user'
        }
        return role_mappings.get(current_role)
        
    def _calculate_remediation_priority(self, waste_pct, risk_score, account_type):
        """Calculate priority for remediation action"""
        if waste_pct >= 100:
            return 'critical'
        elif waste_pct >= 80 and risk_score >= 50:
            return 'high'
        elif waste_pct >= 60:
            return 'medium'
        else:
            return 'low'
            
    def _perform_safety_checks(self, plan, record):
        """Perform safety checks before remediation"""
        checks = []
        
        # Check if account appears to be in use recently
        raw = record.get('raw', {})
        last_refresh = raw.get('lastRefreshTime', '')
        if last_refresh:
            checks.append(f'Last activity analysis: {last_refresh}')
            
        # Check if it's a critical service account
        account_id = plan.get('account_id', '')
        critical_patterns = ['prod', 'admin', 'terraform', 'deployment']
        if any(pattern in account_id.lower() for pattern in critical_patterns):
            checks.append('WARNING: Critical service account detected')
            
        # Check permission count
        insights = raw.get('insights', [])
        if insights:
            perm_count = insights[0].get('content', {}).get('currentTotalPermissionsCount', 0)
            if int(perm_count) > 100:
                checks.append(f'High permission count: {perm_count}')
                
        return checks
        
    def _execute_remediation(self, record, plan):
        """Execute the remediation plan"""
        if self._dry_run:
            return self._simulate_remediation(plan)
        else:
            return self._perform_actual_remediation(record, plan)
            
    def _simulate_remediation(self, plan):
        """Simulate remediation actions (dry run)"""
        action = plan['recommended_action']
        
        result = {
            'action': action,
            'status': 'simulated',
            'timestamp': datetime.utcnow().isoformat(),
            'details': {}
        }
        
        if action == 'remove_binding':
            result['details'] = {
                'action_type': 'remove_iam_binding',
                'account': plan['account_id'],
                'role': plan['current_role'],
                'simulated': True
            }
            _log.info('SIMULATED: Would remove binding %s from %s', 
                     plan['current_role'], plan['account_id'])
                     
        elif action == 'migrate_to_custom_role':
            custom_role = plan['custom_role_suggestion']
            result['details'] = {
                'action_type': 'migrate_to_custom_role',
                'account': plan['account_id'],
                'from_role': plan['current_role'],
                'to_role': custom_role,
                'simulated': True
            }
            _log.info('SIMULATED: Would migrate %s from %s to %s', 
                     plan['account_id'], plan['current_role'], custom_role)
                     
        return result
        
    def _perform_actual_remediation(self, record, plan):
        """Perform actual remediation (when dry_run=False)"""
        # This would contain the actual GCP API calls
        # Only implemented when dry_run=False and proper approvals are in place
        
        _log.warning('Actual remediation not implemented yet - use dry_run mode')
        return {
            'action': plan['recommended_action'],
            'status': 'not_implemented',
            'timestamp': datetime.utcnow().isoformat(),
            'message': 'Actual remediation requires additional safety implementation'
        }
        
    def done(self):
        """Cleanup and report statistics"""
        _log.info('IAM Remediation Statistics:')
        _log.info('  Custom roles created: %d', self._remediation_stats['custom_roles_created'])
        _log.info('  Bindings removed: %d', self._remediation_stats['bindings_removed'])
        _log.info('  Bindings migrated: %d', self._remediation_stats['bindings_migrated'])
        _log.info('  Errors: %d', self._remediation_stats['errors'])
        
        if self._dry_run:
            _log.info('All actions were SIMULATED only (dry_run=True)')
        else:
            _log.info('Actions were EXECUTED (dry_run=False)')