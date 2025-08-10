#!/usr/bin/env python3
"""
Simple test to verify all imports are working correctly.
"""

def test_imports():
    try:
        print("Testing imports...")
        
        # Test basic modules
        import db
        print("✓ db module imported successfully")
        
        import models
        print("✓ models module imported successfully")
        
        import logic
        print("✓ logic module imported successfully")
        
        import seed
        print("✓ seed module imported successfully")
        
        import main
        print("✓ main module imported successfully")
        
        # Test specific classes
        from models import TaxLot, RecentBuy, MarketData, ReplacementPolicy, HarvestItem, HarvestPlan
        print("✓ All model classes imported successfully")
        
        from logic import WashSaleNavigator, demo_policy, explain_plan
        print("✓ All logic functions imported successfully")
        
        print("\n🎉 All imports successful! The application should work correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

if __name__ == "__main__":
    test_imports()
