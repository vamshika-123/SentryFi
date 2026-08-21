import os
import subprocess
import sys

def run_script(script_name):
    script_path = os.path.join(os.path.dirname(__file__), script_name)
    print(f"========================================")
    print(f"Running {script_name}...")
    print(f"========================================")
    
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    print(result.stdout)
    
    if result.returncode != 0:
        print(f"Error running {script_name}:")
        print(result.stderr)
        return False
    return True

def main():
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../models'))
    os.makedirs(models_dir, exist_ok=True)
    
    scripts = [
        "train_phishing.py",
        "train_invoice.py",
        "train_compliance.py"
    ]
    
    all_success = True
    for script in scripts:
        success = run_script(script)
        if not success:
            all_success = False
            
    print("========================================")
    print("Validating generated model artifacts...")
    print("========================================")
    
    expected_models = [
        "phishing_model.joblib",
        "invoice_model.joblib",
        "compliance_model.joblib"
    ]
    
    missing_or_empty = False
    for model_name in expected_models:
        model_path = os.path.join(models_dir, model_name)
        if not os.path.exists(model_path):
            print(f"Missing artifact: {model_name}")
            missing_or_empty = True
        else:
            size = os.path.getsize(model_path)
            if size == 0:
                print(f"Empty artifact: {model_name} (0 bytes)")
                missing_or_empty = True
            else:
                print(f"Found artifact: {model_name} ({size / 1024:.2f} KB)")
                
    if not all_success or missing_or_empty:
        print("\nTraining pipeline finished with errors.")
        sys.exit(1)
    else:
        print("\nAll models trained and saved successfully.")
        sys.exit(0)

if __name__ == "__main__":
    main()
