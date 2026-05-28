# coding=utf-8
import xmlrpclib
import logging
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

def process_account_moves():
    # Get all account move lines with journal ID 8
    account_move_lines = models.execute_kw(db, uid, password, 
        "account.move.line", "search_read",
        [[('journal_id', '=', 8)]],
        {'fields': ['id', 'move_id', 'reconciled']}
    )

    if not account_move_lines:
        print("No account move lines found with journal ID 8")
        return

    # print(f"Found %s account move lines " % len(account_move_lines))
    print len(account_move_lines)

    # Get unique move IDs from the account move lines
    move_ids = list(set(line['move_id'][0] for line in account_move_lines if line['move_id']))

    print "Found %s unique account moves" % len(move_ids)

    # Get all account moves
    account_moves = models.execute_kw(db, uid, password, 
        "account.move", "search_read",
        [[('id', 'in', move_ids), ('journal_id', '=', 8)]],
        {'fields': ['id', 'name', 'state']}
    )

    if not account_moves:
        print("No account moves found")
        return

    print "Found %s account moves" % len(account_moves)
    print "Total  %s account moves" % len(account_moves)

    # # Process each account move
    for move in account_moves:
        move_id = move['id']
        move_name = move['name']
        move_state = move['state']
        
        print "Processing account move:  %s ID: %s, State: %s" % (move_name, move_id, move_state)
        
        # First, cancel reconciliation for all lines in this move
        try:            
            # Set the move to draft state
            if move_state != 'draft':
                print "Setting move %s to draft state" % move_name
                models.execute_kw(db, uid, password, 
                    "account.move", "button_draft",
                    [move_id]
                )
                print "Successfully set move %s to draft state" % move_name
            else:
                print "Move %s is already in draft state" % move_name
                
        except Exception as e:
            print "Error processing move %s: %s" % (move_name, str(e))

if __name__ == '__main__':
    process_account_moves()