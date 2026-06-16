#!/usr/bin/env python3
import os
import platform
if platform.system() == 'Darwin':
    os.environ['SSL_CERT_DIR'] = '/private/etc/ssl/certs'   # Certificate directory
    os.environ['SSL_CERT_FILE'] = '/private/etc/ssl/cert.pem'   # Certificate directory
import websocket
import threading
import sys
import json
import time
import ssl
import argparse
from urllib.parse import urlparse, parse_qs, quote


class WebTerminal:
    def __init__(self, wss_url):
        if not wss_url.startswith('wss://') and not wss_url.startswith('ws://'):
            raise ValueError(f"Invalid WebSocket URL scheme. Expected 'wss://' or 'ws://', got: {wss_url}")
        
        self.terminal_url = wss_url
        self.ws = None
        self.allowed_commands = ['cat', 'cd', 'ls', 'pwd', 'find', 'env', 'grep', 'which']
        self.connected = False
        
    @staticmethod
    def build_ws_url(page_url):
        """Build WebSocket URL from page URL"""
        parsed = urlparse(page_url)
        
        params = parse_qs(parsed.query)
        if 'param' not in params:
            raise ValueError("param parameter not found in URL")
        
        # parse_qs auto-decodes, need to re-encode for wss URL
        param_value = quote(params['param'][0], safe='')
        
        # Note: Server forces HTTPS redirect, must use wss://
        wss_url = f"wss://{parsed.netloc}/terminal/exec?param={param_value}"
        
        return wss_url
    
    def connect(self):
        """Establish WebSocket connection"""
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            self.terminal_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        
        # Disable SSL certificate verification (avoid CERTIFICATE_VERIFY_FAILED errors)
        sslopt = {"cert_reqs": ssl.CERT_NONE}
        
        ws_thread = threading.Thread(target=self.ws.run_forever, kwargs={'sslopt': sslopt})
        ws_thread.daemon = True
        ws_thread.start()
        
        return ws_thread
    
    def on_open(self, ws):
        """Callback when connection is opened"""
        self.connected = True
        print("✓ Connected to terminal")
        self.send_terminal_size()
        
    def on_message(self, ws, message):
        """Callback for receiving messages"""
        if isinstance(message, bytes):
            message = message.decode('utf-8', errors='ignore')
        
        if len(message) > 0:
            code = ord(message[0])
            if 0x2f < code < 0x3a:
                if code == 0x33:
                    error_msg = message[1:]
                    print(f"\n✗ Error: {error_msg}")
                else:
                    output = message[1:]
                    sys.stdout.write(output)
                    sys.stdout.flush()
            elif message.startswith('connected:'):
                print(f"\n{message}")
            elif message.startswith('connectFailed:'):
                print(f"\n✗ {message}")
    
    def on_error(self, ws, error):
        """Error callback"""
        print(f"\n✗ WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """Close callback"""
        self.connected = False
        print(f"\n✗ WebSocket closed: {close_status_code} - {close_msg}")
    
    def send_terminal_size(self):
        """Send terminal size information"""
        try:
            rows, cols = os.popen('stty size', 'r').read().split()
            size_data = {
                "Width": int(cols),
                "Height": int(rows)
            }
            message = "4" + json.dumps(size_data)
            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.send(message)
        except Exception as e:
            print(f"Failed to send terminal size: {e}")
    
    def validate_command(self, command):
        """Validate if command is allowed"""
        cmd = command.strip().split()[0] if command.strip() else ''
        # Command control
        return cmd in self.allowed_commands

    
    def interactive_mode(self):
        """Interactive command mode"""
        print("\n" + "="*50)
        print("Web Terminal Connected")
        print("Allowed commands: cat, cd, ls, pwd")
        print("Type 'exit' to quit")
        print("="*50 + "\n")
        
        try:
            while True:
                if not self.connected:
                    print("\n✗ Not connected to terminal")
                    break
                    
                try:
                    command = input("$ ")
                except EOFError:
                    break
                
                if command.strip().lower() == 'exit':
                    print("Exiting terminal...")
                    break
                
                if not command.strip():
                    continue
                
                if not self.validate_command(command):
                    cmd = command.strip().split()[0]
                    print(f"✗ Error: Command '{cmd}' is not allowed. Only 'cat','cd','ls','pwd','find','env','grep','which' are permitted.")
                    continue
                
                if self.connected and self.ws and self.ws.sock and self.ws.sock.connected:
                    message = "0" + command + "\n"
                    self.ws.send(message)
                else:
                    print("✗ Error: WebSocket not connected")
                    break
                    
        except KeyboardInterrupt:
            print("\n\nInterrupted")
        finally:
            if self.ws and self.ws.sock and self.ws.sock.connected:
                self.ws.close()


def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description='Aliyun ECI Web Terminal Client')
    parser.add_argument('--terminalUrl', required=True, help='Terminal page URL')
    args = parser.parse_args()
    url = args.terminalUrl
    return url


def main():
    print("="*50)
    print("Aliyun ECI Web Terminal Client")
    print("="*50 + "\n")
    
    # Get page URL
    page_url = parse_args()
    
    if not page_url:
        print("✗ Error: URL is required")
        sys.exit(1)
    
    try:
        #print(f"📄 Page URL: {page_url}")
        
        # Build WSS URL
        wss_url = WebTerminal.build_ws_url(page_url)
        #print(f"🔌 WebSocket URL: {wss_url}\n")
        
        # Create terminal instance (validates URL format)
        terminal = WebTerminal(wss_url)
        
        print("Connecting...")
        ws_thread = terminal.connect()
        
        # Wait for connection to establish
        for i in range(6):
            time.sleep(1)
            if terminal.connected:
                break
            if i == 5:
                print("✗ Failed to connect. Please check the URL and try again.")
                sys.exit(1)
        
        terminal.interactive_mode()
        
    except ValueError as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()