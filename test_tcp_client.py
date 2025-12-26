# test_tcp_client.py
# Simple TCP test client for Visualizer protocol testing

import socket
import json
import sys


def test_tcp_client(host="localhost", port=9000):
    """
    Test TCP client that connects to Show Creator's Visualizer server.

    Args:
        host: Server hostname
        port: Server port
    """
    print("=" * 60)
    print("TCP Visualizer Protocol Test Client")
    print("=" * 60)
    print(f"\nConnecting to {host}:{port}...")

    try:
        # Create socket
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.settimeout(10.0)

        # Connect to server
        client_socket.connect((host, port))
        print(f"✓ Connected to server")

        # Receive messages
        message_count = 0
        buffer = ""

        print("\nReceiving configuration messages:\n")

        while True:
            try:
                # Receive data
                data = client_socket.recv(4096)

                if not data:
                    print("\n✗ Server closed connection")
                    break

                # Decode and add to buffer
                buffer += data.decode('utf-8')

                # Process complete messages (newline-delimited)
                while '\n' in buffer:
                    # Extract one message
                    message_str, buffer = buffer.split('\n', 1)

                    if message_str.strip():
                        message_count += 1

                        # Parse JSON
                        try:
                            message = json.loads(message_str)
                            message_type = message.get('type', 'unknown')

                            print(f"[{message_count}] Message type: {message_type}")

                            # Pretty print message content
                            if message_type == "stage":
                                print(f"    Stage: {message['width']}m × {message['height']}m")

                            elif message_type == "fixtures":
                                fixture_count = len(message['fixtures'])
                                print(f"    Fixtures: {fixture_count} total")
                                for i, fixture in enumerate(message['fixtures'][:3]):  # Show first 3
                                    print(f"      [{i+1}] {fixture['name']} ({fixture['manufacturer']} {fixture['model']})")
                                    print(f"          Universe {fixture['universe']}, Address {fixture['address']}")
                                    print(f"          Position: ({fixture['position']['x']}, {fixture['position']['y']}, {fixture['position']['z']})")
                                if fixture_count > 3:
                                    print(f"      ... and {fixture_count - 3} more")

                            elif message_type == "groups":
                                group_count = len(message['groups'])
                                print(f"    Groups: {group_count} total")
                                for i, group in enumerate(message['groups'][:3]):  # Show first 3
                                    print(f"      [{i+1}] {group['name']} (color: {group['color']})")
                                    print(f"          Fixtures: {', '.join(group['fixtures'][:5])}")
                                if group_count > 3:
                                    print(f"      ... and {group_count - 3} more")

                            elif message_type == "heartbeat":
                                print(f"    Heartbeat received")

                            elif message_type == "update":
                                print(f"    Update: {message.get('update_type')}")

                            else:
                                print(f"    Data: {json.dumps(message, indent=2)}")

                            print()

                        except json.JSONDecodeError as e:
                            print(f"✗ Error parsing message: {e}")
                            print(f"   Raw: {message_str}")

                        # Stop after receiving initial config (stage + fixtures + groups)
                        if message_count >= 3 and message_type in ["stage", "fixtures", "groups"]:
                            print("✓ Received complete configuration!")
                            print("\nKeeping connection alive (press Ctrl+C to exit)...")

            except socket.timeout:
                print(".", end="", flush=True)
                continue

    except KeyboardInterrupt:
        print("\n\n✓ Test client stopped by user")
    except ConnectionRefusedError:
        print(f"\n✗ Connection refused. Is the server running on {host}:{port}?")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            client_socket.close()
        except Exception:
            pass

    print("\n" + "=" * 60)
    print(f"Total messages received: {message_count}")
    print("=" * 60)


if __name__ == "__main__":
    # Get host and port from command line or use defaults
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9000

    test_tcp_client(host, port)
