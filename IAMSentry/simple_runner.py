#!/usr/bin/env python3
"""
Simple IAMSentry runner that bypasses multiprocessing issues on Windows
Usage: python simple_runner.py [config_file]
"""

import os
import sys
import json
from datetime import datetime

def main():
    # Add parent directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    sys.path.insert(0, parent_dir)
    
    # Get config file
    config_file = "../my_config.yaml" if len(sys.argv) < 2 else sys.argv[1]
    
    print(f"Starting IAMSentry scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Using config: {config_file}")
    print("=" * 60)
    
    try:
        # Load configuration
        from IAMSentry.helpers.hconfigs import Config
        config = Config.load([config_file])
        
        # Initialize the GCP IAM plugin directly (bypass multiprocessing)
        from IAMSentry.plugins.gcp.gcpcloud import GCPCloudIAMRecommendations
        from IAMSentry.plugins.gcp.gcpcloudiam import GCPIAMRecommendationProcessor
        
        # Get plugin configs
        gcp_reader_config = config['plugins']['gcp_iam_reader']
        gcp_processor_config = config['plugins']['gcp_iam_processor']
        
        # Extract only the parameters that GCPCloudIAMRecommendations accepts
        reader_params = {
            'key_file_path': gcp_reader_config['key_file_path'],
            'projects': gcp_reader_config.get('projects', ['foiply-app']),
            'processes': 1,  # Use single process to avoid multiprocessing issues
            'threads': 1     # Use single thread for simplicity
        }
        
        print("Initializing GCP IAM Reader...")
        reader = GCPCloudIAMRecommendations(**reader_params)
        
        # Extract only the parameters that GCPIAMRecommendationProcessor accepts
        processor_params = {
            'mode_scan': gcp_processor_config.get('mode_scan', True),
            'mode_enforce': gcp_processor_config.get('mode_enforce', False),
            'enforcer': gcp_processor_config.get('enforcer', None)
        }
        
        print("Initializing GCP IAM Processor...")  
        processor = GCPIAMRecommendationProcessor(**processor_params)
        
        print("Reading IAM recommendations from GCP...")
        recommendations = []
        count = 0
        
        try:
            for record in reader.read():
                count += 1
                print(f"   Processing recommendation {count}...")
                
                # Process the record through the processor
                for processed_record in processor.eval(record):
                    recommendations.append(processed_record)
                    
        except Exception as e:
            print(f"WARNING: Error reading recommendations: {e}")
            print("   This might be due to missing GCP permissions.")
            print("   Make sure your service account has 'Recommender Viewer' role.")
            
        print(f"\nResults:")
        print(f"   Found {len(recommendations)} IAM recommendations")
        
        # Save results to file
        if recommendations:
            output_file = "iam_recommendations_results.json"
            with open(output_file, 'w') as f:
                json.dump(recommendations, f, indent=2, default=str)
            print(f"   Results saved to: {output_file}")
            
            # Summary stats
            risk_scores = [r.get('score', {}).get('risk_score', 0) for r in recommendations]
            if risk_scores:
                avg_risk = sum(risk_scores) / len(risk_scores)
                max_risk = max(risk_scores)
                print(f"   Average risk score: {avg_risk:.1f}")
                print(f"   Highest risk score: {max_risk}")
        else:
            print("   No recommendations found (this might indicate permission issues)")
            
        print("\nScan completed successfully!")
        print("=" * 60)
        
        # Cleanup
        reader.done()
        processor.done()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)