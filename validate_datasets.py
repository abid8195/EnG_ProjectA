"""
Automated Dataset Validation and Fixing
Checks all sample datasets and fixes any issues
"""
import os
import pandas as pd
import numpy as np


def validate_and_fix_csv(filepath, expected_cols, label_col, min_rows=100):
    """Validate and fix a CSV dataset"""
    print(f"\n{'='*60}")
    print(f"Validating: {os.path.basename(filepath)}")
    print(f"{'='*60}")
    
    issues_found = []
    fixes_applied = []
    
    # Check if file exists
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False, f"File not found"
    
    try:
        # Load CSV
        df = pd.read_csv(filepath)
        print(f"✓ Loaded successfully: {len(df)} rows, {len(df.columns)} columns")
        
        # Check column names
        if list(df.columns) != expected_cols:
            issues_found.append(f"Column mismatch: expected {expected_cols}, got {list(df.columns)}")
            print(f"❌ Column mismatch")
            print(f"   Expected: {expected_cols}")
            print(f"   Got: {list(df.columns)}")
        else:
            print(f"✓ Columns correct: {expected_cols}")
        
        # Check minimum rows
        if len(df) < min_rows:
            issues_found.append(f"Too few rows: {len(df)} < {min_rows}")
            print(f"❌ Only {len(df)} rows (minimum {min_rows})")
        else:
            print(f"✓ Row count: {len(df)} rows")
        
        # Check for missing values
        missing = df.isnull().sum()
        if missing.any():
            issues_found.append(f"Missing values found: {missing[missing > 0].to_dict()}")
            print(f"❌ Missing values:")
            for col, count in missing[missing > 0].items():
                print(f"   {col}: {count} missing")
            
            # Fix: impute with median for numeric, mode for categorical
            for col in df.columns:
                if df[col].isnull().any():
                    if pd.api.types.is_numeric_dtype(df[col]):
                        df[col].fillna(df[col].median(), inplace=True)
                        fixes_applied.append(f"Imputed {col} with median")
                    else:
                        df[col].fillna(df[col].mode()[0], inplace=True)
                        fixes_applied.append(f"Imputed {col} with mode")
        else:
            print(f"✓ No missing values")
        
        # Check numeric columns
        for col in expected_cols:
            if col == label_col:
                continue  # Label can be categorical
            if not pd.api.types.is_numeric_dtype(df[col]):
                issues_found.append(f"Non-numeric feature: {col}")
                print(f"❌ Column '{col}' is not numeric: {df[col].dtype}")
                
                # Try to convert to numeric
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    fixes_applied.append(f"Converted {col} to numeric")
                    print(f"   ✓ Converted to numeric")
                except:
                    print(f"   ❌ Could not convert to numeric")
            else:
                print(f"✓ '{col}' is numeric: {df[col].dtype}")
        
        # Check label column
        unique_labels = df[label_col].nunique()
        print(f"✓ Label '{label_col}' has {unique_labels} unique values")
        
        # Check for infinite values
        inf_count = np.isinf(df.select_dtypes(include=[np.number])).sum().sum()
        if inf_count > 0:
            issues_found.append(f"Infinite values found: {inf_count}")
            print(f"❌ Found {inf_count} infinite values")
            
            # Replace inf with large finite value
            df.replace([np.inf, -np.inf], np.nan, inplace=True)
            for col in df.select_dtypes(include=[np.number]).columns:
                if df[col].isnull().any():
                    df[col].fillna(df[col].median(), inplace=True)
            fixes_applied.append("Replaced infinite values")
        else:
            print(f"✓ No infinite values")
        
        # Show summary statistics
        print(f"\nSummary Statistics:")
        print(df.describe())
        
        # Apply fixes if any
        if fixes_applied:
            print(f"\n🔧 Applying {len(fixes_applied)} fix(es):")
            for fix in fixes_applied:
                print(f"   • {fix}")
            df.to_csv(filepath, index=False)
            print(f"✓ Fixed file saved: {filepath}")
        
        # Final verdict
        if issues_found and not fixes_applied:
            print(f"\n❌ VALIDATION FAILED: {len(issues_found)} issue(s)")
            for issue in issues_found:
                print(f"   • {issue}")
            return False, issues_found
        elif issues_found and fixes_applied:
            print(f"\n✅ VALIDATION PASSED (after {len(fixes_applied)} fix(es))")
            return True, f"Fixed {len(issues_found)} issues"
        else:
            print(f"\n✅ VALIDATION PASSED (no issues)")
            return True, "No issues"
            
    except Exception as e:
        print(f"❌ Error validating file: {e}")
        return False, str(e)


def main():
    """Main validation routine"""
    print("="*60)
    print("DATASET VALIDATION AND AUTO-FIX")
    print("="*60)
    
    # Define datasets to validate
    script_dir = os.path.dirname(os.path.abspath(__file__))
    uploads_dir = os.path.join(script_dir, 'backend', 'uploads')
    
    datasets = [
        {
            'file': 'iris_like.csv',
            'path': os.path.join(uploads_dir, 'iris_like.csv'),
            'expected_cols': ['sepal_length', 'sepal_width', 'petal_length', 'petal_width', 'species'],
            'label_col': 'species',
            'min_rows': 100
        },
        {
            'file': 'diabetes_small.csv',
            'path': os.path.join(uploads_dir, 'diabetes_small.csv'),
            'expected_cols': ['Glucose', 'BMI', 'Age', 'Insulin', 'BloodPressure', 'Outcome'],
            'label_col': 'Outcome',
            'min_rows': 100
        },
        {
            'file': 'wine_small.csv',
            'path': os.path.join(uploads_dir, 'wine_small.csv'),
            'expected_cols': ['Alcohol', 'Magnesium', 'Flavanoids', 'Proline', 'Class'],
            'label_col': 'Class',
            'min_rows': 100
        }
    ]
    
    results = {}
    
    for dataset in datasets:
        success, message = validate_and_fix_csv(
            dataset['path'],
            dataset['expected_cols'],
            dataset['label_col'],
            dataset['min_rows']
        )
        results[dataset['file']] = {'success': success, 'message': message}
    
    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print(f"{'='*60}")
    
    for filename, result in results.items():
        status = "✅ PASS" if result['success'] else "❌ FAIL"
        print(f"{status} - {filename}")
        print(f"         {result['message']}")
    
    passed = sum(1 for r in results.values() if r['success'])
    total = len(results)
    
    print(f"\n{'='*60}")
    print(f"Total: {total} | Passed: {passed} | Failed: {total - passed}")
    print(f"{'='*60}")
    
    if passed == total:
        print("🎉 All datasets validated successfully!")
        return True
    else:
        print(f"⚠️  {total - passed} dataset(s) failed validation")
        return False


if __name__ == '__main__':
    import sys
    success = main()
    sys.exit(0 if success else 1)
