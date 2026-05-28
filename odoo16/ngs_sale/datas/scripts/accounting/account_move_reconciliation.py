# coding=utf-8
import xmlrpclib
import logging
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

# Get all account move lines with journal ID 8
account_move_lines = models.execute_kw(db, uid, password, 
    "account.move.line", "search_read",
    [[('journal_id', '=', 8)]],
    {'fields': ['id', 'move_id', 'reconciled']}
)

if not account_move_lines:
    __logger.info("No account move lines found with journal ID 8")
    return

__logger.info(f"Found {len(account_move_lines)} account move lines with journal ID 8")

# Get unique move IDs from the account move lines
move_ids = list(set(line['move_id'][0] for line in account_move_lines if line['move_id']))
__logger.info(f"Found {len(move_ids)} unique account moves")

# Get all account moves
account_moves = models.execute_kw(db, uid, password, 
    "account.move", "search_read",
    [[('id', 'in', move_ids)]],
    {'fields': ['id', 'name', 'state']}
)

if not account_moves:
    __logger.info("No account moves found")
    return

__logger.info(f"Found {len(account_moves)} account moves")

# Process each account move
for move in account_moves:
    move_id = move['id']
    move_name = move['name']
    move_state = move['state']
    
    __logger.info(f"Processing account move: {move_name} (ID: {move_id}, State: {move_state})")
    
    # First, cancel reconciliation for all lines in this move
    try:
        # Get all lines for this move
        move_lines = models.execute_kw(db, uid, password, 
            "account.move.line", "search_read",
            [[('move_id', '=', move_id)]],
            {'fields': ['id', 'reconciled']}
        )
        
        # # Unreconcile all lines
        # for line in move_lines:
        #     if line['reconciled']:
        #         __logger.info(f"Unreconciling line ID: {line['id']}")
        #         models.execute_kw(db, uid, password, 
        #             "account.move.line", "remove_move_reconcile",
        #             [line['id']]
        #         )
        
        # # Set the move to draft state
        # if move_state != 'draft':
        #     __logger.info(f"Setting move {move_name} to draft state")
        #     models.execute_kw(db, uid, password, 
        #         "account.move", "button_draft",
        #         [move_id]
        #     )
        #     __logger.info(f"Successfully set move {move_name} to draft state")
        # else:
        #     __logger.info(f"Move {move_name} is already in draft state")
            
    except Exception as e:
        __logger.error(f"Error processing move {move_name}: {str(e)}")