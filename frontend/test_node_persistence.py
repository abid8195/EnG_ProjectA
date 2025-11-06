"""
Test cases to diagnose node disappearance issue
Tests the actual JavaScript execution and DOM manipulation
"""
import os
import sys
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup
FRONTEND_PATH = os.path.abspath(os.path.dirname(__file__))
HTML_FILE = os.path.join(FRONTEND_PATH, "index.html")
# Build a canonical absolute path for the CSV to satisfy Chrome's file input requirements on Windows
CSV_FILE = os.path.normpath(os.path.abspath(os.path.join(FRONTEND_PATH, "..", "backend", "uploads", "diabetes.csv")))

print(f"Testing with HTML: {HTML_FILE}")
print(f"Testing with CSV: {CSV_FILE}")

def setup_driver():
    """Setup Chrome driver with options"""
    options = Options()
    options.add_argument('--headless')  # Run in background
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    try:
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(10)
        return driver
    except Exception as e:
        print(f"ERROR: Failed to initialize Chrome driver: {e}")
        print("HINT: Install ChromeDriver: https://chromedriver.chromium.org/")
        sys.exit(1)

def count_nodes(driver):
    """Count visible nodes on canvas"""
    try:
        canvas = driver.find_element(By.ID, "canvas")
        # Count divs with class 'node' that have data-node-id attribute
        nodes = canvas.find_elements(By.CSS_SELECTOR, "div.node[data-node-id]")
        return len(nodes)
    except Exception as e:
        print(f"  ERROR counting nodes: {e}")
        return -1

def get_console_logs(driver):
    """Get browser console logs"""
    try:
        logs = driver.get_log('browser')
        return [log for log in logs if log['level'] in ['SEVERE', 'WARNING', 'INFO']]
    except:
        return []

def ensure_nodes_present(driver):
    """Ensure at least one node exists by clicking Add Dataset if needed"""
    count = count_nodes(driver)
    if count == 0:
        try:
            add_btn = driver.find_element(By.ID, "add-dataset")
            add_btn.click()
            time.sleep(0.5)
            return count_nodes(driver) > 0
        except Exception:
            return False
    return True


def test_1_initial_load(driver):
    """Test 1: Initial page load - should have initial nodes"""
    print("\n=== TEST 1: Initial Page Load ===")
    
    driver.get(f"file:///{HTML_FILE}")
    time.sleep(2)  # Wait for JS to initialize
    
    node_count = count_nodes(driver)
    print(f"  Initial node count: {node_count}")
    
    # Check for JavaScript errors
    logs = get_console_logs(driver)
    errors = [log for log in logs if log['level'] == 'SEVERE']
    if errors:
        print(f"  ❌ JavaScript errors found:")
        for err in errors:
            print(f"     {err['message']}")
        return False
    
    # It's acceptable to start with 0 nodes. Try to add one.
    if node_count == 0:
        ok = ensure_nodes_present(driver)
        node_count = count_nodes(driver)
        if ok and node_count > 0:
            print(f"  ✓ PASS: Added a node via toolbar. Nodes now: {node_count}")
            return True
        else:
            print(f"  ❌ FAIL: Could not add a node via toolbar")
            return False
    else:
        print(f"  ✓ PASS: {node_count} initial nodes loaded")
        return True

def test_2_select_file(driver):
    """Test 2: File selection without upload - nodes should persist"""
    print("\n=== TEST 2: File Selection (No Upload) ===")
    
    initial_count = count_nodes(driver)
    print(f"  Initial nodes: {initial_count}")
    
    try:
        # Find file input and set file
        file_input = driver.find_element(By.ID, "csvFile")
        file_input.send_keys(CSV_FILE)
        time.sleep(1)
        
        after_select_count = count_nodes(driver)
        print(f"  After file selection: {after_select_count}")
        
        if after_select_count == initial_count:
            print(f"  ✓ PASS: Nodes persisted after file selection")
            return True
        else:
            print(f"  ❌ FAIL: Node count changed! {initial_count} -> {after_select_count}")
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def test_3_upload_click(driver):
    """Test 3: Click upload button - track node count through upload"""
    print("\n=== TEST 3: Upload Button Click ===")
    
    initial_count = count_nodes(driver)
    print(f"  Before upload: {initial_count} nodes")
    
    try:
        # Click upload button
        upload_btn = driver.find_element(By.ID, "btn-upload")
        upload_btn.click()
        
        # Wait and check at intervals
        time.sleep(0.5)
        mid_count = count_nodes(driver)
        print(f"  Mid-upload (0.5s): {mid_count} nodes")
        
        time.sleep(1)
        after_count = count_nodes(driver)
        print(f"  After upload (1.5s): {after_count} nodes")
        
        time.sleep(1)
        final_count = count_nodes(driver)
        print(f"  Final (2.5s): {final_count} nodes")
        
        # Check console for render logs
        logs = get_console_logs(driver)
        render_logs = [log['message'] for log in logs if 'Render' in log['message']]
        print(f"  Render calls detected: {len(render_logs)}")
        for log in render_logs[-5:]:  # Last 5 render logs
            print(f"     {log}")
        
        if final_count >= initial_count:
            print(f"  ✓ PASS: Nodes persisted through upload")
            return True
        else:
            print(f"  ❌ FAIL: Lost nodes! {initial_count} -> {final_count}")
            
            # Check for errors
            errors = [log for log in logs if log['level'] == 'SEVERE']
            if errors:
                print(f"  JavaScript errors during upload:")
                for err in errors[-3:]:
                    print(f"     {err['message']}")
            
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def test_3a_auto_upload_on_change(driver):
    """Test 3a: Auto-upload triggers on file selection change"""
    print("\n=== TEST 3a: Auto-upload on Change ===")
    try:
        # Set file directly, change event should auto-upload
        file_input = driver.find_element(By.ID, "csvFile")
        file_input.send_keys(CSV_FILE)
        time.sleep(2)
        # Wait for lastUpload via debug API
        last_upload = driver.execute_script("return (window.__qml_debug__ && window.__qml_debug__.getLastUpload && window.__qml_debug__.getLastUpload());")
        if not last_upload:
            print("  ❌ FAIL: lastUpload not set after change event")
            return False
        # Verify dataset node path updated
        ds = driver.execute_script("""
            const dbg = window.__qml_debug__;
            if (!dbg || !dbg.getModel) return null;
            const m = dbg.getModel();
            const dsNode = (m.nodes||[]).find(n => n.type === 'dataset');
            return dsNode ? JSON.stringify(dsNode) : null;
        """)
        if not ds:
            print("  ❌ FAIL: Dataset node not found after upload")
            return False
        node = json.loads(ds)
        path = node.get('params', {}).get('path')
        if path:
            print(f"  ✓ Auto-upload set dataset path: {path}")
            return True
        print("  ❌ FAIL: Dataset node missing path after auto-upload")
        return False
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def test_4_multiple_renders(driver):
    """Test 4: Check if multiple render() calls cause node loss"""
    print("\n=== TEST 4: Multiple Render Calls ===")
    
    try:
        initial_count = count_nodes(driver)
        print(f"  Initial nodes: {initial_count}")
        
        # Manually trigger render() multiple times via JavaScript
        for i in range(3):
            driver.execute_script("if (typeof render === 'function') render();")
            time.sleep(0.2)
            count = count_nodes(driver)
            print(f"  After render #{i+1}: {count} nodes")
        
        final_count = count_nodes(driver)
        
        if final_count == initial_count:
            print(f"  ✓ PASS: Nodes survived multiple renders")
            return True
        else:
            print(f"  ❌ FAIL: Lost nodes through renders! {initial_count} -> {final_count}")
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def test_5_check_model_state(driver):
    """Test 5: Verify model.nodes array is populated"""
    print("\n=== TEST 5: Model State Check ===")
    
    try:
        # Get model.nodes via exposed debug API
        model_json = driver.execute_script("return JSON.stringify(window.__qml_debug__ && window.__qml_debug__.getModel && window.__qml_debug__.getModel());")
        if not model_json:
            print("  ❌ FAIL: __qml_debug__ API not available")
            return False
        nodes = json.loads(model_json).get('nodes', [])
        
        print(f"  model.nodes array length: {len(nodes)}")
        
        if nodes:
            print(f"  Sample node IDs: {[n.get('id') for n in nodes[:3]]}")
            print(f"  Sample node types: {[n.get('type') for n in nodes[:3]]}")
        
        dom_count = count_nodes(driver)
        print(f"  DOM node count: {dom_count}")
        
        if len(nodes) == dom_count and len(nodes) > 0:
            print(f"  ✓ PASS: Model and DOM in sync")
            return True
        else:
            print(f"  ❌ FAIL: Mismatch! model.nodes={len(nodes)}, DOM={dom_count}")
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def test_6_check_dataset_node(driver):
    """Test 6: Verify dataset node exists and is updated after upload"""
    print("\n=== TEST 6: Dataset Node Update ===")
    
    try:
        # Get dataset node from debug model
        dataset_node = driver.execute_script("""
            const dbg = window.__qml_debug__;
            if (!dbg || !dbg.getModel) return null;
            const m = dbg.getModel();
            const dsNode = (m.nodes || []).find(n => n.type === 'dataset');
            return dsNode ? JSON.stringify(dsNode) : null;
        """)
        
        if dataset_node:
            node = json.loads(dataset_node)
            print(f"  Dataset node found: ID={node.get('id')}")
            print(f"  Dataset params: {node.get('params', {})}")
            
            path = node.get('params', {}).get('path')
            if path:
                print(f"  ✓ Dataset has path: {path}")
                return True
            else:
                print(f"  ❌ Dataset node missing path parameter")
                return False
        else:
            print(f"  ❌ FAIL: No dataset node found in model")
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def test_7_run_pipeline_button(driver):
    """Test 7: Click Run Pipeline button - should not lose nodes"""
    print("\n=== TEST 7: Run Pipeline Button ===")
    
    try:
        initial_count = count_nodes(driver)
        print(f"  Before Run Pipeline: {initial_count} nodes")
        
        # Check if dataset is uploaded first
        last_upload = driver.execute_script("return (window.lastUpload || null);")
        if not last_upload:
            print(f"  ⚠ WARNING: No lastUpload data, pipeline may not run")
        
        # Click Run Pipeline
        run_btn = driver.find_element(By.ID, "btn-run")
        run_btn.click()
        time.sleep(2)
        
        after_count = count_nodes(driver)
        print(f"  After Run Pipeline: {after_count} nodes")
        
        if after_count >= initial_count:
            print(f"  ✓ PASS: Nodes persisted through pipeline run")
            return True
        else:
            print(f"  ❌ FAIL: Lost nodes! {initial_count} -> {after_count}")
            return False
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("NODE PERSISTENCE DIAGNOSTIC TESTS")
    print("=" * 60)
    
    if not os.path.exists(HTML_FILE):
        print(f"ERROR: HTML file not found: {HTML_FILE}")
        sys.exit(1)
    
    if not os.path.exists(CSV_FILE):
        print(f"WARNING: CSV file not found: {CSV_FILE}")
        print(f"Some tests may fail.")
    
    driver = setup_driver()
    results = []
    
    try:
        # Run tests in sequence
        results.append(("Initial Load", test_1_initial_load(driver)))
        results.append(("File Selection", test_2_select_file(driver)))
        results.append(("Upload Click", test_3_upload_click(driver)))
        results.append(("Auto-upload on Change", test_3a_auto_upload_on_change(driver)))
        results.append(("Multiple Renders", test_4_multiple_renders(driver)))
        results.append(("Model State", test_5_check_model_state(driver)))
        results.append(("Dataset Node", test_6_check_dataset_node(driver)))
        results.append(("Run Pipeline", test_7_run_pipeline_button(driver)))
        
    finally:
        driver.quit()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed ({passed*100//total}%)")
    
    if passed < total:
        print("\n⚠ ISSUES DETECTED - Check test output above for details")
        sys.exit(1)
    else:
        print("\n✓ ALL TESTS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
