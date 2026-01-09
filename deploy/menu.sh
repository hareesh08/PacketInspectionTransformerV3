#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Print banner
print_banner() {
    clear
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                                                                ║${NC}"
    echo -e "${CYAN}║     ${WHITE}Packet Inspection Transformer - Deployment Menu${NC}          ${CYAN}║${NC}"
    echo -e "${CYAN}║                                                                ║${NC}"
    echo -e "${CYAN}║     ${GREEN}Real-time Malware Detection Platform${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}║                                                                ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Check script dependencies
check_scripts() {
    local missing=0
    
    if [ ! -f "$SCRIPT_DIR/setup.sh" ]; then
        log_warn "setup.sh not found"
        missing=1
    fi
    
    if [ ! -f "$SCRIPT_DIR/run.sh" ]; then
        log_warn "run.sh not found"
        missing=1
    fi
    
    if [ ! -f "$SCRIPT_DIR/restart.sh" ]; then
        log_warn "restart.sh not found"
        missing=1
    fi
    
    if [ ! -f "$SCRIPT_DIR/clean.sh" ]; then
        log_warn "clean.sh not found"
        missing=1
    fi
    
    if [ $missing -eq 1 ]; then
        log_error "Some scripts are missing. Please ensure all scripts are in the same directory."
        exit 1
    fi
    
    # Make scripts executable
    chmod +x "$SCRIPT_DIR/setup.sh" 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/restart.sh" 2>/dev/null || true
    chmod +x "$SCRIPT_DIR/clean.sh" 2>/dev/null || true
}

# Check system status
check_system_status() {
    echo -e "${CYAN}┌────────────────────────────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│ ${WHITE}System Status${NC}                                              ${CYAN}│${NC}"
    echo -e "${CYAN}├────────────────────────────────────────────────────────────────┤${NC}"
    echo -e "${CYAN}│${NC} $(date '+%Y-%m-%d %H:%M:%S')                                     ${CYAN}│${NC}"
    echo -e "${CYAN}│${NC}                                                            ${CYAN}│${NC}"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1)
        echo -e "${CYAN}│${NC} ${GREEN}✓ Python${NC}: $PYTHON_VERSION                                ${CYAN}│${NC}"
    else
        echo -e "${CYAN}│${NC} ${RED}✗ Python${NC}: Not installed                                  ${CYAN}│${NC}"
    fi
    
    # Check Node.js
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        echo -e "${CYAN}│${NC} ${GREEN}✓ Node.js${NC}: $NODE_VERSION                                ${CYAN}│${NC}"
    else
        echo -e "${CYAN}│${NC} ${RED}✗ Node.js${NC}: Not installed                                 ${CYAN}│${NC}"
    fi
    
    # Check Nginx
    if command -v nginx &> /dev/null; then
        echo -e "${CYAN}│${NC} ${GREEN}✓ Nginx${NC}: Installed                                      ${CYAN}│${NC}"
    else
        echo -e "${CYAN}│${NC} ${RED}✗ Nginx${NC}: Not installed                                   ${CYAN}│${NC}"
    fi
    
    # Check virtual environment
    if [ -d "/opt/packet-inspection-transformer/venv" ]; then
        echo -e "${CYAN}│${NC} ${GREEN}✓ Virtualenv${NC}: Created                                   ${CYAN}│${NC}"
    else
        echo -e "${CYAN}│${NC} ${YELLOW}○ Virtualenv${NC}: Not created                               ${CYAN}│${NC}"
    fi
    
    # Check frontend build
    if [ -d "/opt/packet-inspection-transformer/dashboard/dist" ]; then
        echo -e "${CYAN}│${NC} ${GREEN}✓ Frontend${NC}: Built                                       ${CYAN}│${NC}"
    else
        echo -e "${CYAN}│${NC} ${YELLOW}○ Frontend${NC}: Not built                                   ${CYAN}│${NC}"
    fi
    
    # Check model file
    if [ -f "/opt/packet-inspection-transformer/model/finetuned_best_model.pth" ]; then
        echo -e "${CYAN}│${NC} ${GREEN}✓ Model${NC}: Uploaded                                       ${CYAN}│${NC}"
    else
        echo -e "${CYAN}│${NC} ${RED}✗ Model${NC}: Not uploaded (upload via SCP)                   ${CYAN}│${NC}"
    fi
    
    echo -e "${CYAN}│${NC}                                                            ${CYAN}│${NC}"
    echo -e "${CYAN}└────────────────────────────────────────────────────────────────┘${NC}"
}

# Option 1: Full Setup
option_setup() {
    echo ""
    log_info "Starting Full Setup..."
    echo ""
    
    if [ "$EUID" -ne 0 ]; then
        log_warn "Not running as root, will use sudo for setup commands"
        sudo "$SCRIPT_DIR/setup.sh"
    else
        "$SCRIPT_DIR/setup.sh"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

# Option 2: Run Services
option_run() {
    echo ""
    log_info "Starting Services..."
    echo ""
    
    if [ "$EUID" -ne 0 ]; then
        sudo "$SCRIPT_DIR/run.sh"
    else
        "$SCRIPT_DIR/run.sh"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

# Option 3: Restart Services
option_restart() {
    echo ""
    log_info "Restarting Services..."
    echo ""
    
    if [ "$EUID" -ne 0 ]; then
        sudo "$SCRIPT_DIR/restart.sh"
    else
        "$SCRIPT_DIR/restart.sh"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

# Option 4: Clean All
option_clean() {
    echo ""
    log_warn "This will remove all installed components!"
    echo ""
    
    if [ "$EUID" -ne 0 ]; then
        sudo "$SCRIPT_DIR/clean.sh"
    else
        "$SCRIPT_DIR/clean.sh"
    fi
    
    echo ""
    read -p "Press Enter to continue..."
}

# Option 5: Exit
option_exit() {
    echo ""
    log_info "Goodbye!"
    echo ""
    exit 0
}

# Main menu loop
main_menu() {
    local choice
    
    while true; do
        print_banner
        check_system_status
        echo ""
        echo -e "${CYAN}┌────────────────────────────────────────────────────────────────┐${NC}"
        echo -e "${CYAN}│ ${WHITE}Main Menu${NC}                                                ${CYAN}│${NC}"
        echo -e "${CYAN}├────────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${CYAN}│${NC}                                                            ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}   ${WHITE}1)${NC}  Full Setup                                       ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}   ${WHITE}2)${NC}  Run Services                                     ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}   ${WHITE}3)${NC}  Restart Services                                 ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}   ${WHITE}4)${NC}  Clean All                                        ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}   ${WHITE}5)${NC}  Exit                                            ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}                                                            ${CYAN}│${NC}"
        echo -e "${CYAN}├────────────────────────────────────────────────────────────────┤${NC}"
        echo -e "${CYAN}│${NC}   ${GREEN}Quick Access:${NC}                                        ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}   Dashboard: http://<VM_PUBLIC_IP>                           ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}   API:       http://<VM_PUBLIC_IP>/api                       ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}   Health:    http://<VM_PUBLIC_IP>/health                    ${CYAN}│${NC}"
        echo -e "${CYAN}│${NC}                                                            ${CYAN}│${NC}"
        echo -e "${CYAN}└────────────────────────────────────────────────────────────────┘${NC}"
        echo ""
        echo -e "${WHITE}Enter your choice [1-5]:${NC} "
        read choice
        
        case $choice in
            1) option_setup ;;
            2) option_run ;;
            3) option_restart ;;
            4) option_clean ;;
            5) option_exit ;;
            *)
                echo ""
                log_error "Invalid choice. Please enter 1-5."
                sleep 2
                ;;
        esac
    done
}

# Entry point
main() {
    check_scripts
    main_menu
}

# Run main
main "$@"