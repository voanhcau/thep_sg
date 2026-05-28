# -*- coding: utf-8 -*-
"""
Script to post Inventory Valuation Moves from Draft to Posted
Filter conditions:
- Journal = "inventory valuation"
- Current state = "Draft"
- Database: erp.thepnamsaigon.com (production)

Purpose: Fix Purchase Order invoice creation error due to qty_received = 0
after running script 02_update_inventory_valuation_to_draft.py
"""
try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib
import time
import logging
import sys
import codecs
import os

# Set UTF-8 encoding for stdout
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

__logger = logging.getLogger(__name__)

# Connection config - import from login_local
from login_local import uid, password, db, models

def post_inventory_valuation_moves():
    """Post Inventory Valuation Moves from Draft to Posted"""
    try:
        # Find journal with name "inventory valuation"
        print("Finding journal 'inventory valuation'...")
        all_journals = models.execute_kw(db, uid, password, 
            "account.journal", "search_read",
            [[]],
            {'fields': ['id', 'name', 'code', 'type']}
        )
        
        # Filter journals containing "inventory valuation"
        journal_ids = []
        for journal in all_journals:
            if 'inventory valuation' in journal['name'].lower():
                journal_ids.append(journal['id'])
                print("  - %s (Code: %s, Type: %s)" % (
                    journal['name'], 
                    journal['code'],
                    journal['type']
                ))
        
        if not journal_ids:
            print("No journal 'inventory valuation' found!")
            return
        
        print("Found %d journal(s)" % len(journal_ids))
        print()
        
        # Find account moves with inventory valuation journal and state = draft
        print("Finding Account Moves to post...")
        print("Conditions:")
        print("  - Journal: inventory valuation")
        print("  - State: draft")
        
        # Domain to filter account moves
        domain = [
            ('journal_id', 'in', journal_ids),
            ('state', '=', 'draft')
        ]
        
        # Get account moves info
        account_moves = models.execute_kw(db, uid, password,
            'account.move', 'search_read',
            [domain],
            {'fields': ['name', 'journal_id', 'state', 'amount_total', 'date', 'ref']})
        
        if not account_moves:
            print("No Account Moves found to post!")
            print("All inventory valuation moves are already posted.")
            return
        
        print("  Total Account Moves to post:", len(account_moves))
        
        # Show some info before posting
        print("STATISTICS BEFORE POSTING:")
        print("  Total Account Moves:", len(account_moves))
        print()
        
        # Show some info before posting
        print("ACCOUNT MOVES DETAILS (first 5 lines):")
        print("-" * 120)
        print("%-8s %-15s %-20s %-15s %-15s %-15s %-10s" % (
            "ID", "Name", "Journal", "Date", "Amount Total", "State", "Lines"
        ))
        print("-" * 120)
        
        total_amount = 0
        for i, move in enumerate(account_moves[:5]):  # Show first 5 lines
            journal_name = move.get('journal_id', [False, 'N/A'])[1] if move.get('journal_id') else 'N/A'
            amount = move.get('amount_total', 0)
            total_amount += amount
            
            # Count lines in move
            try:
                line_count = models.execute_kw(db, uid, password, 
                    "account.move.line", "search_count",
                    [('move_id', '=', move['id'])]
                )
            except:
                line_count = 0
            
            print("%-8s %-15s %-20s %-15s %-15.2f %-10s %-10s" % (
                move['id'],
                move.get('name', '')[:14],
                journal_name[:19],
                move.get('date', 'N/A'),
                amount,
                move.get('state', 'N/A'),
                line_count
            ))
        
        if len(account_moves) > 5:
            print("... and %d other moves" % (len(account_moves) - 5))
        
        print("-" * 120)
        print("Total moves: %d, Total amount: %.2f" % (len(account_moves), total_amount))
        print("-" * 120)
        
        # Confirm before posting
        print("\nWARNING:")
        print("You are about to POST %d Account Moves from 'draft' to 'posted'." % len(account_moves))
        print("This will:")
        print("  - Restore stock valuation layers")
        print("  - Update qty_received in stock moves")
        print("  - Fix Purchase Order invoice creation error")
        
        # Allow non-interactive confirmation via AUTO_CONFIRM environment variable
        auto_confirm = os.environ.get('AUTO_CONFIRM', '').lower()
        confirm = auto_confirm if auto_confirm in ('y', 'n') else input("\nAre you sure you want to continue? (y/n): ").lower().strip()
        if confirm != 'y':
            print("Operation cancelled.")
            return
        
        print("\nStarting to POST moves...")
        
        # Post each account move
        success_count = 0
        error_count = 0
        
        for i, move in enumerate(account_moves, 1):
            try:
                move_id = move['id']
                move_name = move['name']
                
                # Check current state
                current_state = models.execute_kw(db, uid, password,
                    'account.move', 'read',
                    [move_id], {'fields': ['state']})[0]['state']
                
                if current_state == 'draft':
                    # Post move by calling action_post
                    models.execute_kw(db, uid, password,
                        'account.move', 'action_post',
                        [move_id])
                    
                    # Check state after posting
                    new_state = models.execute_kw(db, uid, password,
                        'account.move', 'read',
                        [move_id], {'fields': ['state']})[0]['state']
                    
                    if new_state == 'posted':
                        print("  [%d/%d] SUCCESS %s: Posted successfully" % (i, len(account_moves), move_name))
                        success_count += 1
                    else:
                        print("  [%d/%d] WARNING %s: State after post: %s" % (i, len(account_moves), move_name, new_state))
                        success_count += 1
                elif current_state == 'posted':
                    print("  [%d/%d] INFO %s: Already in posted state" % (i, len(account_moves), move_name))
                    success_count += 1
                else:
                    print("  [%d/%d] WARNING %s: Unexpected state: %s" % (i, len(account_moves), move_name, current_state))
                    error_count += 1
                
            except Exception as e:
                print("  [%d/%d] ERROR %s: %s" % (i, len(account_moves), move_name, str(e)))
                error_count += 1
                __logger.error("Error posting move %s: %s" % (move_name, str(e)))
            
            # Pause every 100 moves to avoid overload
            if i % 100 == 0:
                print("    ... Processed %d/%d moves, pausing 2 seconds ..." % (i, len(account_moves)))
                time.sleep(2)
        
        print("\nPOSTING RESULTS:")
        print("  Success:", success_count)
        print("  Errors:", error_count)
        print("  Total:", len(account_moves))
        
        # Check again after posting
        print("\nVERIFYING RESULTS AFTER POSTING:")
        updated_moves = models.execute_kw(db, uid, password, 
            "account.move", "search_read",
            [domain],
            {'fields': ['id', 'name', 'state']}
        )
        
        posted_count = sum(1 for move in updated_moves if move.get('state') == 'posted')
        draft_count = sum(1 for move in updated_moves if move.get('state') == 'draft')
        print("  Posted moves: %d/%d" % (posted_count, len(updated_moves)))
        print("  Draft moves: %d/%d" % (draft_count, len(updated_moves)))
        
        if draft_count == 0:
            print("\nSUCCESS: All inventory valuation moves have been posted!")
            print("Purchase Order invoice creation error has been fixed.")
        else:
            print("\nWARNING: Still %d moves not posted. Need further investigation." % draft_count)
        
    except Exception as e:
        print("ERROR: %s" % str(e))
        __logger.error("Post moves error: %s" % str(e))

def main():
    """Main function"""
    start_time = time.time()
    print("==========================================")
    print("SCRIPT POST INVENTORY VALUATION MOVES")
    print("==========================================")
    print("Start time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Database:", db)
    print("User ID:", uid)
    print("Purpose: Fix PO invoice creation error")
    print()
    
    try:
        post_inventory_valuation_moves()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n==========================================")
        print("COMPLETED")
        print("==========================================")
        print("End time:", time.strftime("%Y-%m-%d %H:%M:%S"))
        print("Processing time: %.2f seconds" % duration)
        
    except Exception as e:
        print("FATAL ERROR: %s" % str(e))
        __logger.error("Script error: %s" % str(e))

if __name__ == '__main__':
    main()