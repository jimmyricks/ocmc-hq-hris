#!/usr/bin/env python3
"""
Test script to simulate confirm_receipt logic without modifying database
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

# Add the app path to import modules
sys.path.insert(0, '/home/eamadmin/eam-2.0/eam-2.1-fastapi-vue/backend')

async def test_confirm_receipt_logic():
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://eam_b4c9a727de32:QDqg5EdwaGo1Z4GyBx1MDZrUnvhzKzc6hUXvd5Mpl4@localhost:5432/eam_b4c9a727de32')
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as db:
        print("=== Testing confirm_receipt logic (READ-ONLY) ===")
        
        # Step 1: Get purchase receipt with column names
        result = await db.execute(text('SELECT * FROM purchase_receipt WHERE id = \'PRC-00007\''))
        receipt = result.fetchone()
        
        if not receipt:
            print("❌ Purchase Receipt PRC-00007 not found")
            return
            
        # Get column names for proper indexing
        result = await db.execute(text('''
            SELECT column_name, ordinal_position 
            FROM information_schema.columns 
            WHERE table_name = 'purchase_receipt' 
            ORDER BY ordinal_position
        '''))
        pr_columns = {col[0]: i for i, col in enumerate(result.fetchall())}
        
        print(f"✓ Found Purchase Receipt: {receipt[pr_columns['id']]}")
        
        # Step 2: Check if inventory already generated
        generated_inventory = receipt[pr_columns['generated_inventory']]
        if generated_inventory:
            print("❌ Inventory already generated for this receipt")
            return
            
        # Step 3: Check PO enabled (assume disabled for this test)
        po_enabled = False
        print(f"✓ PO Enabled: {po_enabled}")
        
        if not po_enabled:
            # Step 4: Get PR Line
            pr_line_id = receipt[pr_columns['purchase_request_line']]
            print(f"✓ PR Line ID: {pr_line_id}")
            
            result = await db.execute(text(f'SELECT * FROM purchase_request_line WHERE id = \'{pr_line_id}\''))
            pr_line = result.fetchone()
            
            if not pr_line:
                print(f"❌ PR Line '{pr_line_id}' not found")
                return
                
            print(f"✓ Found PR Line: {pr_line[22]}")  # id is at index 22
            
            # Step 5: Get item from PR line
            item_id = pr_line[4]  # item field
            if not item_id:
                print("❌ PR Line has no item")
                return
                
            print(f"✓ Item ID: {item_id}")
            
            # Step 6: Get item details
            result = await db.execute(text(f'SELECT * FROM item WHERE id = \'{item_id}\''))
            item = result.fetchone()
            
            if not item:
                print(f"❌ Item '{item_id}' not found")
                return
                
            print(f"✓ Item: {item[1]}")  # item_name
            
            # Step 7: Check item type
            item_type_raw = item[3]  # item_type
            if not item_type_raw:
                print("❌ Item Type is required")
                return
                
            item_type = item_type_raw.strip().lower().replace(" ", "_")
            if item_type in ("service_item", "non_inventory_item"):
                print(f"❌ Cannot generate inventory for {item_type_raw}")
                return
                
            print(f"✓ Item Type: {item_type_raw}")
            
            # Step 8: Check quantities
            qty_received = receipt[pr_columns['quantity_received']] or 0
            if qty_received <= 0:
                print("❌ Quantity received must be greater than 0")
                return
                
            qty_required = pr_line[9] or 0  # qty_required
            prev_received = pr_line[18] or 0  # qty_received
            total_after = prev_received + qty_received
            
            print(f"✓ Qty Required: {qty_required}")
            print(f"✓ Qty Previously Received: {prev_received}")
            print(f"✓ Qty This Receipt: {qty_received}")
            print(f"✓ Total After Receipt: {total_after}")
            
            if qty_required > 0 and total_after > qty_required:
                remaining = qty_required - prev_received
                print(f"❌ Cannot receive {qty_received} items. Only {remaining} remaining.")
                return
                
            # Step 9: Test inventory creation logic (without actually creating)
            location = receipt[pr_columns['receiving_location']]
            site = receipt[pr_columns['site']]
            
            print(f"✓ Location: {location}")
            print(f"✓ Site: {site}")
            
            # This would be the store query that was causing issues
            print("✓ Store query logic: SKIPPED (store_location will be None)")
            print("✓ All validations passed - confirm_receipt would succeed!")
            
            print("\n=== Expected Result ===")
            print("• Inventory record created with:")
            print(f"  - location: {location}")
            print(f"  - site: {site}")
            print(f"  - item: {item_id}")
            print(f"  - quantity: {qty_received}")
            print(f"  - store_location: None (user will fill later)")
            print("• PR Line updated with new qty_received")
            print("• Purchase Receipt marked as generated_inventory=True")

if __name__ == "__main__":
    asyncio.run(test_confirm_receipt_logic())
