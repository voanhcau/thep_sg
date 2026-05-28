#!/bin/bash
# Setup New Company - Helper Script
# Script này giúp export và import cấu hình kế toán dễ dàng hơn

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Setup New Company - Accounting Configuration${NC}"
echo ""

# Check arguments
if [ $# -lt 2 ]; then
    echo -e "${RED}Usage:${NC}"
    echo "  $0 [env] [action] [options...]"
    echo ""
    echo -e "${YELLOW}Actions:${NC}"
    echo "  export [company_id]              - Export config from source company"
    echo "  import [config_file] [company_id] [company_name] - Import config to target company"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 local export 1"
    echo "  $0 local import accounting_config_company_1_20250101_120000.json 2 'Công Ty Mới'"
    exit 1
fi

ENV_TYPE=$1
ACTION=$2

case $ACTION in
    export)
        if [ -z "$3" ]; then
            echo -e "${RED}Error: Company ID required${NC}"
            echo "Usage: $0 $ENV_TYPE export [company_id]"
            exit 1
        fi
        COMPANY_ID=$3
        echo -e "${GREEN}📤 Exporting accounting configuration...${NC}"
        python3 export_accounting_config.py "$ENV_TYPE" "$COMPANY_ID"
        ;;
    
    import)
        if [ -z "$3" ] || [ -z "$4" ]; then
            echo -e "${RED}Error: Config file and company ID required${NC}"
            echo "Usage: $0 $ENV_TYPE import [config_file] [company_id] [company_name]"
            exit 1
        fi
        CONFIG_FILE=$3
        COMPANY_ID=$4
        COMPANY_NAME=${5:-""}
        
        if [ ! -f "$CONFIG_FILE" ]; then
            echo -e "${RED}Error: Config file not found: $CONFIG_FILE${NC}"
            exit 1
        fi
        
        echo -e "${GREEN}📥 Importing accounting configuration...${NC}"
        if [ -n "$COMPANY_NAME" ]; then
            python3 import_accounting_config.py "$ENV_TYPE" "$CONFIG_FILE" "$COMPANY_ID" "$COMPANY_NAME"
        else
            python3 import_accounting_config.py "$ENV_TYPE" "$CONFIG_FILE" "$COMPANY_ID"
        fi
        ;;
    
    *)
        echo -e "${RED}Error: Unknown action: $ACTION${NC}"
        echo "Valid actions: export, import"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}✅ Done!${NC}"
